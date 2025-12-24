"""
Music Server - Runs as a standalone service with complete playlist management
Start this once and it keeps running, handling all music operations.

To run:
python music_server.py

The server will run on http://localhost:5555
"""

import os
import sys
import threading
import time
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
from collections import deque
from pathlib import Path
import random
import sqlite3
import pickle
from flask_socketio import SocketIO, emit
from flask_cors import cross_origin
from flask import send_from_directory, send_file

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))



from dotenv import dotenv_values
env_vars = dotenv_values(".env")

try:
    import vlc
except ImportError:
    print("ERROR: python-vlc is required. Install with: pip install python-vlc")
    sys.exit(1)


from yt_db import add_music_entry, get_media_info, get_conn, get_playlist_id, is_song_in_playlist, ensure_table
from ply_yt_2 import download_audio, download_video, search_youtube
from music_cli import start_server_in_background, stop_server_in_background

    
last_alive = time.time()
HEARTBEAT_TIMEOUT = 5  # seconds


DB_PATH = env_vars.get("DB_PATH")
# ==============================================================================
# MUSIC PLAYER ENGINE
# ==============================================================================

class MusicEngine:
    """Core music player engine that the server uses."""
    
    def __init__(self):
        # Check if we should show the VLC display (default to True if not set)
        show_display = os.environ.get('SHOW_VLC_DISPLAY', '1').lower() in ('1', 'true', 'yes')
        
        # Configure VLC instance based on display preference
        if show_display:
            # Normal VLC instance with display
            self.vlc_instance = vlc.Instance()
        else:
            # VLC instance with no video output
            vlc_args = ['--no-video']
            self.vlc_instance = vlc.Instance(' '.join(vlc_args))
        
        self.player = self.vlc_instance.media_player_new()
        
        # Store display preference
        self.show_display = show_display
        
        # State
        self.current_song = None
        self.queue = deque()
        self.playlists = {}
        self.current_playlist = []
        self.current_playlist_name = None
        self.playlist_index = 0
        self.history = deque(maxlen=50)
        
        # Settings
        self.is_playing = False
        self.volume = 75
        self.is_muted = False
        self.shuffle = False
        self.repeat = 'off'  # off, one, all

        ensure_table()

        # Monitor thread
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        # Initialize database for playlists
        self._init_playlist_db()
        
        # Load library and saved playlists
        self._load_library()
        self._load_saved_playlists()
        
    def _init_playlist_db(self):
        """Initialize playlist database tables."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            
            # Create playlists table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    modified_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create playlist_songs table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS playlist_songs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_id INTEGER NOT NULL,
                    song_data TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
                )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Failed to init playlist DB: {e}")
    
    def _monitor_loop(self):
        """Monitor playback and handle song transitions."""
        while self.running:
            if self.player and self.current_song and self.is_playing:
                state = self.player.get_state()
                if state == vlc.State.Ended:
                    print("Song ended, playing next...")
                    self._handle_song_end()
            time.sleep(0.5)
    
    def _handle_song_end(self):
        """Handle what happens when a song ends."""
        if self.repeat == 'one':
            self.play_file(self.current_song['file_location'])
        elif self.queue:
            next_song = self.queue.popleft()
            self.play_file(next_song['file_location'])
        elif self.current_playlist:
            self.playlist_index += 1
            if self.playlist_index >= len(self.current_playlist):
                if self.repeat == 'all':
                    self.playlist_index = 0
                else:
                    self.stop()
                    return
            self.play_file(self.current_playlist[self.playlist_index]['file_location'])
        else:
            self.stop()
    
    def play_file(self, file_path):
        """Play a file directly."""
        if not os.path.exists(file_path):
            return {'error': f'File not found: {file_path}'}
        
        self.player.stop()
        media = self.vlc_instance.media_new(file_path)
        self.player.set_media(media)
        self.player.play()
        
        # Wait for player to start
        time.sleep(0.1)
        
        # Try to get more info about the song
        song_info = self._get_song_info(file_path)
        if song_info:
            self.current_song = song_info
        else:
            self.current_song = {
                'file_location': file_path,
                'title': os.path.basename(file_path),
                'name': os.path.splitext(os.path.basename(file_path))[0]
            }
        
        self.is_playing = True
        self.history.append(self.current_song)
        
        if not self.is_muted:
            self.player.audio_set_volume(self.volume)
        
        return {'status': 'playing', 'song': self.current_song}
    
    def play_by_name(self, name):
        """Search and play a song by name."""
        # First check if it's a file path
        if os.path.exists(name):
            return self.play_file(name)
        
        # Search in database
        try:
            conn = get_conn()
            cur = conn.cursor()
            
            # Try exact match
            cur.execute(
                "SELECT file_location, name, singer, duration FROM music WHERE LOWER(name) = LOWER(?) LIMIT 1",
                (name,)
            )
            result = cur.fetchone()
            
            if not result:
                # Try partial match
                cur.execute(
                    "SELECT file_location, name, singer, duration FROM music WHERE LOWER(name) LIKE LOWER(?) LIMIT 1",
                    (f"%{name}%",)
                )
                result = cur.fetchone()
            
            conn.close()
            
            if result:
                self.current_song = {
                    'file_location': result[0],
                    'name': result[1],
                    'title': result[1],
                    'singer': result[2] if len(result) > 2 else None,
                    'duration': result[3] if len(result) > 3 else None
                }
                return self.play_file(result[0])
            else:
                return {'error': f'Song not found: {name}'}
                
        except Exception as e:
            return {'error': f'Database error: {str(e)}'}
    
    def pause(self):
        """Pause playback."""
        if self.is_playing:
            self.player.pause()
            self.is_playing = False
            return {'status': 'paused'}
        return {'status': 'already_paused'}
    
    def resume(self):
        """Resume playback."""
        if not self.is_playing and self.current_song:
            self.player.play()
            self.is_playing = True
            return {'status': 'resumed'}
        return {'status': 'nothing_to_resume'}
    
    def stop(self):
        """Stop playback."""
        self.player.stop()
        self.is_playing = False
        self.current_song = None
        self.current_playlist_name = None
        return {'status': 'stopped'}
    
    def next(self):
        """Play next song."""
        if self.queue:
            next_song = self.queue.popleft()
            return self.play_file(next_song['file_location'])
        elif self.current_playlist:
            self.playlist_index += 1
            if self.playlist_index >= len(self.current_playlist):
                if self.repeat == 'all':
                    self.playlist_index = 0
                else:
                    return {'status': 'end_of_playlist'}
            return self.play_file(self.current_playlist[self.playlist_index]['file_location'])
        else:
            return {'status': 'no_next_song'}
    
    def previous(self):
        """Play previous song."""
        if self.current_playlist and self.playlist_index > 0:
            self.playlist_index -= 1
            return self.play_file(self.current_playlist[self.playlist_index]['file_location'])
        elif len(self.history) >= 2:
            self.history.pop()  # Remove current
            prev = self.history[-1]
            return self.play_file(prev['file_location'])
        elif self.current_song:
            self.seek(0)
            return {'status': 'restarted'}
        return {'status': 'no_previous_song'}
    
    def add_to_queue(self, song_name):
        """Add song to queue."""
        # Search for the song
        song_data = self._search_song(song_name)
        if song_data:
            self.queue.append(song_data)
            return {'status': 'added_to_queue', 'song': song_data}
        return {'error': f'Song not found: {song_name}'}
    
    def clear_queue(self):
        """Clear the queue."""
        self.queue.clear()
        return {'status': 'queue_cleared'}
    
    def remove_from_queue(self, index):
        """Remove song at index from queue."""
        try:
            if 0 <= index < len(self.queue):
                queue_list = list(self.queue)
                removed = queue_list.pop(index)
                self.queue = deque(queue_list)
                return {'status': 'removed_from_queue', 'song': removed}
            return {'error': 'Invalid queue index'}
        except Exception as e:
            return {'error': str(e)}
    
    def set_volume(self, level):
        """Set volume (0-100)."""
        self.volume = max(0, min(100, level))
        if not self.is_muted:
            self.player.audio_set_volume(self.volume)
        return {'volume': self.volume}
    
    def toggle_mute(self):
        """Toggle mute."""
        if self.is_muted:
            self.is_muted = False
            self.player.audio_set_volume(self.volume)
        else:
            self.is_muted = True
            self.player.audio_set_volume(0)
        return {'muted': self.is_muted}
    
    def seek(self, position):
        """Seek to position in seconds."""
        if self.current_song:
            self.player.set_time(int(position * 1000))
            return {'position': position}
        return {'error': 'No song playing'}
    
    def set_repeat(self, mode):
        """Set repeat mode: off, one, all."""
        if mode in ['off', 'one', 'all']:
            self.repeat = mode
            return {'repeat': mode}
        return {'error': 'Invalid repeat mode'}
    
    def set_shuffle(self, enabled):
        """Enable/disable shuffle."""
        self.shuffle = enabled
        if enabled and self.current_playlist:
            # Shuffle remaining songs
            remaining = self.current_playlist[self.playlist_index + 1:]
            random.shuffle(remaining)
            self.current_playlist = self.current_playlist[:self.playlist_index + 1] + remaining
        return {'shuffle': enabled}
    
    # ==============================================================================
    # PLAYLIST MANAGEMENT
    # ==============================================================================
    
    def create_playlist(self, name, songs=None):
        """Create a playlist and save to database."""
        if name in self.playlists:
            return {'error': f'Playlist "{name}" already exists'}
        
        try:
            # Save to database
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute('INSERT INTO playlists (name) VALUES (?)', (name,))
            playlist_id = cur.lastrowid
            
            # Add songs if provided
            if songs:
                for i, song in enumerate(songs):
                    song_json = json.dumps(song)
                    cur.execute(
                        'INSERT INTO playlist_songs (playlist_id, song_data, position) VALUES (?, ?, ?)',
                        (playlist_id, song_json, i)
                    )
            
            conn.commit()
            conn.close()
            
            # Update memory
            self.playlists[name] = songs or []
            return {'status': 'playlist_created', 'name': name, 'song_count': len(songs) if songs else 0}
            
        except Exception as e:
            return {'error': f'Failed to create playlist: {str(e)}'}
    
    def delete_playlist(self, name):
        """Delete a playlist."""
        if name == 'Library':
            return {'error': 'Cannot delete Library playlist'}
        
        if name not in self.playlists:
            return {'error': f'Playlist "{name}" not found'}
        
        try:
            # Delete from database
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute('DELETE FROM playlists WHERE name = ?', (name,))
            conn.commit()
            conn.close()
            
            # Remove from memory
            del self.playlists[name]
            
            # If it was the current playlist, clear it
            if self.current_playlist_name == name:
                self.current_playlist = []
                self.current_playlist_name = None
                self.playlist_index = 0
            
            return {'status': 'playlist_deleted', 'name': name}
            
        except Exception as e:
            return {'error': f'Failed to delete playlist: {str(e)}'}
    
    def add_to_playlist(self, playlist_name, song_name):
        """Add a song to an existing playlist."""
        if playlist_name not in self.playlists:
            return {'error': f'Playlist "{playlist_name}" not found'}
        # Search for the song
        song_data = self._search_song(song_name)
        if not song_data:
            # Try to get it as a file path
            if os.path.exists(song_name):
                song_data = {
                    'file_location': song_name,
                    'name': os.path.splitext(os.path.basename(song_name))[0],
                    'title': os.path.splitext(os.path.basename(song_name))[0]
                }
            else:
                return {'error': f'Song not found: {song_name}'}
        
        try:
            # Get playlist ID
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute('SELECT id FROM playlists WHERE name = ?', (playlist_name,))
            result = cur.fetchone()
            
            if result:
                playlist_id = result[0]
                position = len(self.playlists[playlist_name])
                song_json = json.dumps(song_data)
                
                cur.execute(
                    'INSERT INTO playlist_songs (playlist_id, song_data, position) VALUES (?, ?, ?)',
                    (playlist_id, song_json, position)
                )
                conn.commit()
            
            conn.close()
            
            # Update memory
            self.playlists[playlist_name].append(song_data)
            
            # If this playlist is currently playing, update it
            if self.current_playlist_name == playlist_name:
                self.current_playlist.append(song_data)
            
            return {'status': 'song_added_to_playlist', 'playlist': playlist_name, 'song': song_data}
            
        except Exception as e:
            return {'error': f'Failed to add song to playlist: {str(e)}'}
    
    def remove_from_playlist(self, playlist_name, index):
        """Remove a song from a playlist by index."""
        if playlist_name not in self.playlists:
            return {'error': f'Playlist "{playlist_name}" not found'}
        
        if playlist_name == 'Library':
            return {'error': 'Cannot modify Library playlist'}
        
        playlist = self.playlists[playlist_name]
        if not (0 <= index < len(playlist)):
            return {'error': 'Invalid song index'}
        
        try:
            removed_song = playlist[index]
            
            # Update database
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            
            # Get playlist ID
            cur.execute('SELECT id FROM playlists WHERE name = ?', (playlist_name,))
            result = cur.fetchone()
            
            if result:
                playlist_id = result[0]
                
                # Remove the song
                cur.execute(
                    'DELETE FROM playlist_songs WHERE playlist_id = ? AND position = ?',
                    (playlist_id, index)
                )
                
                # Update positions of remaining songs
                cur.execute(
                    'UPDATE playlist_songs SET position = position - 1 WHERE playlist_id = ? AND position > ?',
                    (playlist_id, index)
                )
                
                conn.commit()
            
            conn.close()
            
            # Update memory
            playlist.pop(index)
            
            # If this playlist is currently playing, update it
            if self.current_playlist_name == playlist_name:
                self.current_playlist.pop(index)
                # Adjust current index if needed
                if self.playlist_index > index:
                    self.playlist_index -= 1
            
            return {'status': 'song_removed_from_playlist', 'playlist': playlist_name, 'song': removed_song}
            
        except Exception as e:
            return {'error': f'Failed to remove song from playlist: {str(e)}'}
    
    def reorder_playlist(self, playlist_name, from_index, to_index):
        """Reorder songs in a playlist."""
        if playlist_name not in self.playlists:
            return {'error': f'Playlist "{playlist_name}" not found'}
        
        if playlist_name == 'Library':
            return {'error': 'Cannot reorder Library playlist'}
        
        playlist = self.playlists[playlist_name]
        if not (0 <= from_index < len(playlist) and 0 <= to_index < len(playlist)):
            return {'error': 'Invalid indices'}
        
        try:
            # Reorder in memory
            song = playlist.pop(from_index)
            playlist.insert(to_index, song)
            
            # Update database
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            
            # Get playlist ID
            cur.execute('SELECT id FROM playlists WHERE name = ?', (playlist_name,))
            result = cur.fetchone()
            
            if result:
                playlist_id = result[0]
                
                # Clear and re-insert all songs with new positions
                cur.execute('DELETE FROM playlist_songs WHERE playlist_id = ?', (playlist_id,))
                
                for i, song_data in enumerate(playlist):
                    song_json = json.dumps(song_data)
                    cur.execute(
                        'INSERT INTO playlist_songs (playlist_id, song_data, position) VALUES (?, ?, ?)',
                        (playlist_id, song_json, i)
                    )

                
                conn.commit()
            
            conn.close()
            
            # If this playlist is currently playing, update it
            if self.current_playlist_name == playlist_name:
                song = self.current_playlist.pop(from_index)
                self.current_playlist.insert(to_index, song)
                
                # Adjust current index if needed
                if self.playlist_index == from_index:
                    self.playlist_index = to_index
                elif from_index < self.playlist_index <= to_index:
                    self.playlist_index -= 1
                elif to_index <= self.playlist_index < from_index:
                    self.playlist_index += 1
            
            return {'status': 'playlist_reordered', 'playlist': playlist_name}
            
        except Exception as e:
            return {'error': f'Failed to reorder playlist: {str(e)}'}
    
    def play_playlist(self, name):
        """Play a playlist."""
        if name not in self.playlists:
            return {'error': f'Playlist "{name}" not found'}
        
        playlist = self.playlists[name]
        if not playlist:
            return {'error': f'Playlist "{name}" is empty'}
        
        self.current_playlist = playlist.copy()
        self.current_playlist_name = name
        self.playlist_index = 0
        
        if self.shuffle:
            random.shuffle(self.current_playlist)
        
        return self.play_file(self.current_playlist[0]['file_location'])
    
    def get_playlist_songs(self, playlist_name):
        """Get all songs in a playlist."""
        if playlist_name not in self.playlists:
            return {'error': f'Playlist "{playlist_name}" not found'}
        
        return {
            'playlist': playlist_name,
            'songs': self.playlists[playlist_name],
            'count': len(self.playlists[playlist_name])
        }
    
    def rename_playlist(self, old_name, new_name):
        """Rename a playlist."""
        if old_name == 'Library':
            return {'error': 'Cannot rename Library playlist'}
        
        if old_name not in self.playlists:
            return {'error': f'Playlist "{old_name}" not found'}
        
        if new_name in self.playlists:
            return {'error': f'Playlist "{new_name}" already exists'}
        
        try:
            # Update database
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute('UPDATE playlists SET name = ? WHERE name = ?', (new_name, old_name))
            conn.commit()
            conn.close()
            
            # Update memory
            self.playlists[new_name] = self.playlists.pop(old_name)
            
            # Update current playlist name if it's playing
            if self.current_playlist_name == old_name:
                self.current_playlist_name = new_name
            
            return {'status': 'playlist_renamed', 'old_name': old_name, 'new_name': new_name}
            
        except Exception as e:
            return {'error': f'Failed to rename playlist: {str(e)}'}
    
    def duplicate_playlist(self, playlist_name, new_name=None):
        """Duplicate a playlist."""
        if playlist_name not in self.playlists:
            return {'error': f'Playlist "{playlist_name}" not found'}
        
        if not new_name:
            new_name = f"{playlist_name} (Copy)"
            i = 1
            while new_name in self.playlists:
                i += 1
                new_name = f"{playlist_name} (Copy {i})"
        
        if new_name in self.playlists:
            return {'error': f'Playlist "{new_name}" already exists'}
        
        songs = self.playlists[playlist_name].copy()
        return self.create_playlist(new_name, songs)
    
    def get_status(self):
        """Get current player status."""
        position = 0
        duration = 0
        
        if self.current_song and self.is_playing:
            position = self.player.get_time() / 1000.0
            duration = self.current_song.get('duration', 0)
        
        return {
            'is_playing': self.is_playing,
            'current_song': self.current_song,
            'current_playlist': self.current_playlist_name,
            'playlist_index': self.playlist_index if self.current_playlist else None,
            'position': position,
            'duration': duration,
            'volume': self.volume,
            'muted': self.is_muted,
            'repeat': self.repeat,
            'shuffle': self.shuffle,
            'queue_size': len(self.queue),
            'queue': list(self.queue)[:5]  # First 5 items
        }
    
    def search_songs(self, query, limit=10):
        """Search for songs in database."""
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""
                SELECT file_location, name, singer, duration, genre 
                FROM music 
                WHERE LOWER(name) LIKE LOWER(?) 
                LIMIT ?
            """, (f"%{query}%", limit))
            
            rows = cur.fetchall()
            conn.close()
            
            return [{
                'file_location': row[0],
                'name': row[1],
                'title': row[1],
                'singer': row[2] if len(row) > 2 else None,
                'duration': row[3] if len(row) > 3 else None,
                'genre': row[4] if len(row) > 4 else None
            } for row in rows]
        except:
            return []
    
    def _search_song(self, query):
        """Search for a single song."""
        songs = self.search_songs(query, 1)
        return songs[0] if songs else None
    
    def _get_song_info(self, file_path):
        """Get song info from database by file path."""
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "SELECT name, singer, duration, genre FROM music WHERE file_location = ?",
                (file_path,)
            )
            result = cur.fetchone()
            conn.close()
            
            if result:
                return {
                    'file_location': file_path,
                    'name': result[0],
                    'title': result[0],
                    'singer': result[1] if len(result) > 1 else None,
                    'duration': result[2] if len(result) > 2 else None,
                    'genre': result[3] if len(result) > 3 else None
                }
        except:
            pass
        return None
    
    def _load_library(self):
        """Load all songs into Library playlist."""
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT file_location, name, singer, duration FROM music")
            rows = cur.fetchall()
            conn.close()
            
            library = [{
                'file_location': row[0],
                'name': row[1],
                'title': row[1],
                'singer': row[2] if len(row) > 2 else None,
                'duration': row[3] if len(row) > 3 else None
            } for row in rows]
            
            self.playlists['Library'] = library
            print(f"Loaded {len(library)} songs into Library")
        except Exception as e:
            print(f"Failed to load library: {e}")
            self.playlists['Library'] = []
    
    def _load_saved_playlists(self):
        """Load saved playlists from database."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            
            # Get all playlists
            cur.execute('SELECT id, name FROM playlists')
            playlists = cur.fetchall()
            
            for playlist_id, name in playlists:
                # Get songs for this playlist
                cur.execute(
                    'SELECT song_data FROM playlist_songs WHERE playlist_id = ? ORDER BY position',
                    (playlist_id,)
                )
                songs_data = cur.fetchall()
                
                songs = []
                for song_json, in songs_data:
                    try:
                        song = json.loads(song_json)
                        songs.append(song)
                    except:
                        pass
                
                self.playlists[name] = songs
                print(f"Loaded playlist '{name}' with {len(songs)} songs")
            
            conn.close()
            
        except Exception as e:
            print(f"Failed to load saved playlists: {e}")
        
# ==============================================================================
# FLASK SERVER - ENHANCED PLAYLIST ROUTES
# ==============================================================================

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests
engine = MusicEngine()
CORS(app, origins="*", supports_credentials=True)
# socketio = SocketIO(app, cors_allowed_origins="*")

# Existing routes (preserved)...

@app.route('/play', methods=['POST'])
def play():
    data = request.json
    song = data.get('song')
    if not song:
        return jsonify({'error': 'No song specified'}), 400
    return jsonify(engine.play_by_name(song))

@app.route('/pause', methods=['POST'])
def pause():
    return jsonify(engine.pause())

@app.route('/resume', methods=['POST'])
def resume():
    return jsonify(engine.resume())

@app.route('/stop', methods=['POST'])
def stop():
    return jsonify(engine.stop())

@app.route('/next', methods=['POST'])
def next_song():
    return jsonify(engine.next())

@app.route('/previous', methods=['POST'])
def previous_song():
    return jsonify(engine.previous())

@app.route('/queue/add', methods=['POST'])
def add_to_queue():
    data = request.json
    song = data.get('song')
    if not song:
        return jsonify({'error': 'No song specified'}), 400
    return jsonify(engine.add_to_queue(song))

@app.route('/queue/clear', methods=['POST'])
def clear_queue():
    return jsonify(engine.clear_queue())

@app.route('/queue/remove', methods=['POST'])
def remove_from_queue():
    data = request.json
    index = data.get('index')
    if index is None:
        return jsonify({'error': 'No index specified'}), 400
    return jsonify(engine.remove_from_queue(index))

@app.route('/queue', methods=['GET'])
def get_queue():
    return jsonify({'queue': list(engine.queue)})

@app.route('/volume', methods=['POST'])
def set_volume():
    data = request.json
    level = data.get('level')
    if level is None:
        return jsonify({'error': 'No volume level specified'}), 400
    return jsonify(engine.set_volume(level))

@app.route('/volume/up', methods=['POST'])
def volume_up():
    return jsonify(engine.set_volume(engine.volume + 10))

@app.route('/volume/down', methods=['POST'])
def volume_down():
    return jsonify(engine.set_volume(engine.volume - 10))

@app.route('/mute', methods=['POST'])
def toggle_mute():
    return jsonify(engine.toggle_mute())

@app.route('/seek', methods=['POST'])
def seek():
    data = request.json
    position = data.get('position')
    if position is None:
        return jsonify({'error': 'No position specified'}), 400
    return jsonify(engine.seek(position))

@app.route('/repeat', methods=['POST'])
def set_repeat():
    data = request.json
    mode = data.get('mode', 'off')
    return jsonify(engine.set_repeat(mode))

@app.route('/shuffle', methods=['POST'])
def set_shuffle():
    data = request.json
    enabled = data.get('enabled', False)
    return jsonify(engine.set_shuffle(enabled))

# ==============================================================================
# ENHANCED PLAYLIST ROUTES
# ==============================================================================

@app.route('/playlist/create', methods=['POST'])
def create_playlist():
    data = request.json
    name = data.get('name')
    # print("Creating playlist:", name)
    songs = data.get('songs', [])
    if not name:
        return jsonify({'error': 'No playlist name specified'}), 400
    return jsonify(engine.create_playlist(name, songs))

@app.route('/playlist/delete', methods=['POST'])
def delete_playlist():
    data = request.json
    name = data.get('name')
    if not name:
        return jsonify({'error': 'No playlist name specified'}), 400
    return jsonify(engine.delete_playlist(name))

@app.route('/playlist/play', methods=['POST'])
def play_playlist():
    data = request.json
    name = data.get('name')
    if not name:
        return jsonify({'error': 'No playlist name specified'}), 400
    return jsonify(engine.play_playlist(name))

@app.route('/playlist/add_song', methods=['POST'])
def add_song_to_playlist():
    data = request.json
    playlist_name = data.get('playlist')
    song_name = data.get('song')
    if not playlist_name or not song_name:
        return jsonify({'error': 'Playlist and song name required'}), 400
    return jsonify(engine.add_to_playlist(playlist_name, song_name))

@app.route('/playlist/remove_song', methods=['POST'])
def remove_song_from_playlist():
    data = request.json
    playlist_name = data.get('playlist')
    index = data.get('index')
    if not playlist_name or index is None:
        return jsonify({'error': 'Playlist name and index required'}), 400
    return jsonify(engine.remove_from_playlist(playlist_name, index))

@app.route('/playlist/reorder', methods=['POST'])
def reorder_playlist():
    data = request.json
    playlist_name = data.get('playlist')
    from_index = data.get('from_index')
    to_index = data.get('to_index')
    if not playlist_name or from_index is None or to_index is None:
        return jsonify({'error': 'Playlist name and indices required'}), 400
    return jsonify(engine.reorder_playlist(playlist_name, from_index, to_index))

@app.route('/playlist/rename', methods=['POST'])
def rename_playlist():
    data = request.json
    old_name = data.get('old_name')
    new_name = data.get('new_name')
    if not old_name or not new_name:
        return jsonify({'error': 'Old and new names required'}), 400
    return jsonify(engine.rename_playlist(old_name, new_name))

@app.route('/playlist/duplicate', methods=['POST'])
def duplicate_playlist():
    data = request.json
    playlist_name = data.get('playlist')
    new_name = data.get('new_name')
    if not playlist_name:
        return jsonify({'error': 'Playlist name required'}), 400
    return jsonify(engine.duplicate_playlist(playlist_name, new_name))

@app.route('/playlist/<name>', methods=['GET'])
def get_playlist_details(name):
    return jsonify(engine.get_playlist_songs(name))

@app.route('/playlists', methods=['GET'])
def get_playlists():
    return jsonify({
        'playlists': {name: len(songs) for name, songs in engine.playlists.items()},
        'current': engine.current_playlist_name
    })
    

# In music_server.py, update the toggle_display endpoint:
@app.route('/display/toggle', methods=['POST'])
def toggle_display():
    """Toggle the VLC display on/off (requires server restart)."""
    try:
        # Toggle the display setting in the environment
        current = os.environ.get('SHOW_VLC_DISPLAY', '1').lower() in ('1', 'true', 'yes')
        new_setting = '0' if current else '1'
        os.environ['SHOW_VLC_DISPLAY'] = new_setting
        
        # Update the engine's display setting
        engine.show_display = not current
        
        return jsonify({
            'status': 'success',
            'message': 'Display setting updated. Please restart the server for changes to take effect.',
            'current_display': not current
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status', methods=['GET'])
def status():
    data = engine.get_status()
    data['show_display'] = engine.show_display
    return jsonify(data)

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({'status': 'alive'})



@app.route('/library', methods=['GET', 'OPTIONS'])
@cross_origin()
def get_library():
    """Get all downloaded songs."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT file_location, name, singer, duration, genre 
            FROM music 
            ORDER BY added_date DESC
        """)
        rows = cur.fetchall()
        conn.close()
        
        songs = [{
            'file_location': row[0],
            'name': row[1],
            'title': row[1],
            'singer': row[2] if len(row) > 2 else None,
            'duration': row[3] if len(row) > 3 else None,
            'genre': row[4] if len(row) > 4 else None
        } for row in rows]
        
        return jsonify({'songs': songs})
    except Exception as e:
        print(f"Library error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/youtube/search', methods=['GET', 'OPTIONS'])
@cross_origin()
def youtube_search():
    """Search YouTube videos."""
    try:
        query = request.args.get('q', '')
        limit = request.args.get('limit', 10, type=int)
        
        if not query:
            return jsonify({'error': 'No query provided'}), 400
            
        results = search_youtube(query, max_results=limit)
        return jsonify({'results': results})
    except Exception as e:
        print(f"YouTube search error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/youtube/download', methods=['POST', 'OPTIONS'])
@cross_origin()
def youtube_download():
    """Download from YouTube."""
    try:
        
        data = request.json
        query = data.get('query')
        mode = data.get('mode', 'audio')  # 'audio' or 'video'
        play_after = data.get('play_after', False)
        
        if not query:
            return jsonify({'error': 'No query provided'}), 400
            
        if mode == 'video':
            result = download_video(query, use_search=True)
        else:
            result = download_audio(query, use_search=True)
        
        return jsonify({
            'status': 'success',
            'result': result
        })
    except Exception as e:
        print(f"YouTube download error: {e}")
        return jsonify({'error': str(e)}), 500

# Also update the /search endpoint to handle limit parameter:
@app.route('/search', methods=['GET', 'OPTIONS'])
@cross_origin()
def search():
    query = request.args.get('q')
    limit = request.args.get('limit', 10, type=int)
    if not query:
        return jsonify({'error': 'No search query'}), 400
    return jsonify({'results': engine.search_songs(query, limit)})

if __name__ == '__main__':
    print("=" * 60)
    print("MUSIC SERVER STARTING")
    print("Server will run at: http://localhost:5555")
    print("Keep this terminal open while using the music player")
    print("=" * 60)
    # app.run(host='0.0.0.0', port=5555, debug=True, use_reloader=True)

    app.run(
        host='0.0.0.0',
        port=5555,
        debug=False,
        use_reloader=False
        )
