"""
YouTube search / play / download helpers with Music Server Client.

This is the CLIENT that communicates with the music server.
Import this in your scripts to control music playback.

The music server must be running for playback to work:
python music_server.py

Example usage:
from play_yt import player, search_youtube, download_audio

# Play a song (non-blocking, returns immediately)
player.play_local("believer")

# Control playback
player.pause()
player.resume()
player.set_volume(80)
player.next()

# Playlist management
player.create_playlist("My Favorites")
player.add_to_playlist("My Favorites", "shape of you")
player.play_playlist("My Favorites")
"""

import sys
import os
import requests
import json
import subprocess
import time
import webbrowser
from typing import List, Dict, Optional, Union
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from dotenv import dotenv_values
env_vars = dotenv_values(".env")

# Server configuration
MUSIC_SERVER_URL = env_vars.get("MUSIC_SERVER_URL")

# Paths
_PROJECT_ROOT = Path(__file__).resolve().parent
print("THE PROJECT ROOT:", _PROJECT_ROOT)
_DEFAULT_DOWNLOAD_ROOT = _PROJECT_ROOT / 'data' / 'downloads' / 'music'
AUDIO_DOWNLOAD_DIR = str(_DEFAULT_DOWNLOAD_ROOT / 'audio')
VIDEO_DOWNLOAD_DIR = str(_DEFAULT_DOWNLOAD_ROOT / 'video')

os.makedirs(AUDIO_DOWNLOAD_DIR, exist_ok=True)
os.makedirs(VIDEO_DOWNLOAD_DIR, exist_ok=True)
 

DB_PATH = env_vars.get("DB_PATH")

try:
    from yt_dlp import YoutubeDL
except:
    YoutubeDL = None


from db.yt_db import add_music_entry, get_media_info, get_conn, get_playlist_id, get_song_from_db, is_song_in_playlist


# ==============================================================================
# ORIGINAL HELPER FUNCTIONS (ALL PRESERVED)
# ==============================================================================

def _ensure_yt_dlp():
    if YoutubeDL is None:
        raise RuntimeError("yt-dlp is required. Install with: pip install yt-dlp")

def js_runtime_available() -> bool:
    import shutil
    return shutil.which('node') is not None

def pretty(obj):
    """Pretty print JSON in console without changing return values."""
    try:
        print(json.dumps(obj, indent=2, ensure_ascii=False))
    except:
        print(obj)

def search_youtube(query: str, max_results: int = 5) -> List[Dict]:
    """Search YouTube and return a list of result metadata."""
    _ensure_yt_dlp()
    if not query: return []
    
    search_query = f"ytsearch{max_results}:{query}"
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'extractor_args': {
            'youtube': {
                'player_client': 'default'
                }
            },
        'cookies': 'E:\\Adi_32GR_files\\MyCodingHelper\\Projects\\python_projects\\Jarvis_V2_Alpha\\data\\cookies.txt',
        

    }
    
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_query, download=False)
    
    entries = info.get('entries', [])
    return [{
        'id': e.get('id'),
        'title': e.get('title'),
        'webpage_url': e.get('webpage_url') or e.get('url'),
        'duration': e.get('duration'),
        'uploader': e.get('uploader'),
    } for e in entries or []]

def play_youtube(target: str, use_search: bool = False) -> Optional[str]:
    """Open YouTube video in browser."""
    if not target: return None
    
    if use_search:
        results = search_youtube(target, max_results=1)
        if not results: return None
        url = results[0]['webpage_url']
    else:
        url = target
    
    webbrowser.open(url)
    return url

def list_downloaded_songs() -> List[Dict]:
    """List all downloaded songs from database."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, name, singer, duration, genre, file_location FROM music ORDER BY added_date DESC")
        rows = cur.fetchall()
        conn.close()
        result = [{
            'id': r[0], 'name': r[1], 'singer': r[2],
            'duration': r[3], 'genre': r[4],
            'file_location': r[5] if len(r) > 5 else None
        } for r in rows]
        return result
    except Exception as e:
        print(f'Error querying database: {e}')
        return []

def download_audio(url_or_query: str, out_template: str = '%(title)s.%(ext)s',
                  use_search: bool = False, download_dir: Optional[str] = None,
                  auto_db: bool = True) -> Dict:
    """Download audio from YouTube."""
    _ensure_yt_dlp()
    existing = get_song_from_db(url_or_query)
    if existing:
        pretty({
            "status": "already_exists",
            "file": existing["file_location"],
            "metadata": existing
        })
        return {
            "status": "already_exists",
            "file": existing["file_location"],
            "metadata": existing
        }
    if use_search:
        results = search_youtube(url_or_query, max_results=1)
        if not results: raise ValueError('No search results')
        url = results[0]['webpage_url']
    else:
        url = url_or_query
    
    if not download_dir: download_dir = AUDIO_DOWNLOAD_DIR
    if not os.path.isabs(out_template) and not os.path.dirname(out_template):
        out_template = os.path.join(download_dir, out_template)
    os.makedirs(download_dir, exist_ok=True)
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_template,
        'quiet': False,
        'extractor_args': {
            'youtube': {
                'player_client': 'default'
                }
            },
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'cookies': 'E:\\Adi_32GR_files\\MyCodingHelper\\Projects\\python_projects\\Jarvis_V2_Alpha\\data\\cookies.txt',
        
    }
    
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        try:
            base = ydl.prepare_filename(info)
            final = os.path.splitext(base)[0] + '.mp3'
            info['file_path'] = os.path.abspath(final if os.path.exists(final) else base)
        except: pass
    
    if auto_db and 'file_path' in info:
        try:
            media_info = get_media_info(info['file_path'])
            add_music_entry(
                file_location=info['file_path'],
                name=info.get('title'), 
                metadata=info, 
                singer=info.get('uploader'),
                duration=media_info.get('duration'), 
                genre='audio'
                )
            print(f'✓ Registered in DB: {info.get("title")}')
        except: pass
    
    return info

def download_video(url_or_query: str, out_template: str = '%(title)s.%(ext)s',
                  use_search: bool = False, merge_format: str = 'mkv',
                  auto_db: bool = True) -> Dict:
    """Download video from YouTube."""
    _ensure_yt_dlp()
    
    existing = get_song_from_db(url_or_query)
    if existing:
        pretty({
            "status": "already_exists",
            "file": existing["file_location"],
            "metadata": existing
        })
        return {
            "status": "already_exists",
            "file": existing["file_location"],
            "metadata": existing
        }
    if use_search:
        results = search_youtube(url_or_query, max_results=1)
        if not results: raise ValueError('No search results')
        url = results[0]['webpage_url']
    else:
        url = url_or_query
    
    if not os.path.isabs(out_template) and not os.path.dirname(out_template):
        out_template = os.path.join(VIDEO_DOWNLOAD_DIR, out_template)
    
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': out_template,
        'merge_output_format': merge_format,
        'quiet': False,
        'extractor_args': {'youtube': {'player_client': 'default'}},
        'cookies': 'E:\\Adi_32GR_files\\MyCodingHelper\\Projects\\python_projects\\Jarvis_V2_Alpha\\data\\cookies.txt',
        
    }
    
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        try:
            base = ydl.prepare_filename(info)
            final = os.path.splitext(base)[0] + '.' + merge_format
            info['file_path'] = os.path.abspath(final if os.path.exists(final) else base)
        except: pass
    
    if auto_db and 'file_path' in info:
        try:
            media_info = get_media_info(info['file_path'])
            add_music_entry(
                file_location=info['file_path'],
                name=info.get('title'),
                metadata=info,
                singer=info.get('uploader'),
                duration=media_info.get('duration'),
                genre='Video'
            )
            print(f'✓ Registered in DB: {info.get("title")}')
        except: pass
    
    return {
                "file_location" : info['file_path'],
                "name" : info.get('title'),
                "singer" : info.get('uploader'),
                "duration" : media_info.get('duration'),
                "genre" : 'Video'
    }

# ==============================================================================
# ENHANCED MUSIC PLAYER CLIENT
# ==============================================================================

class MusicPlayer:
    """
    Client for the Music Server with complete playlist management.
    Sends HTTP requests to control playback.
    ALL methods are non-blocking and return immediately.
    """
    
    def __init__(self):
        self.server_url = MUSIC_SERVER_URL
        # self._ensure_server_running()
    
    def _ensure_server_running(self):
        """Check if server is running, start it if not."""
        try:
            response = requests.get(f"{self.server_url}/ping", timeout=1)
            if response.status_code == 200:
                print("Music server is running")
                return True
        except:
            print("Music server not running. Starting it...")
            # Try to start the server
            server_script = r"E:\Adi_32GR_files\MyCodingHelper\Projects\python_projects\Jarvis_V2_Alpha\services\tools\music_player\music_server.py"
            if os.path.exists(server_script):
                subprocess.Popen(['python', server_script], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
                time.sleep(3)  # Give server time to start
                try:
                    response = requests.get(f"{self.server_url}/ping", timeout=1)
                    if response.status_code == 200:
                        print("Music server started successfully")
                        return True
                except:
                    pass
            print("WARNING: Could not start music server. Please run 'python music_server.py' manually.")
            return False
    
    def _request(self, method, endpoint, data=None, params=None):
        """Make a request to the server."""
        try:
            url = f"{self.server_url}{endpoint}"
            if method == 'GET':
                response = requests.get(url, params=params, timeout=2)
            else:
                response = requests.post(url, json=data, timeout=2)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Server communication error: {e}")
            return {'error': 'Server not available'}
    
    # ==============================================================================
    # PLAYBACK CONTROLS
    # ==============================================================================
    
    def play_local(self, song: str) -> bool:
        """Play a song by name or path."""
        result = self._request('POST', '/play', {'song': song})
        return result
    
    def play(self, song: Union[Dict, str]) -> bool:
        """Play a song."""
        if isinstance(song, dict):
            song = song.get('file_location', song.get('name', ''))
        return self.play_local(song)
    
    def pause(self) -> bool:
        """Pause playback."""
        result = self._request('POST', '/pause')
        
        return 'error' not in result
    
    def resume(self) -> bool:
        """Resume playback."""
        result = self._request('POST', '/resume')
        
        return 'error' not in result
    
    def stop(self) -> bool:
        """Stop playback."""
        result = self._request('POST', '/stop')
       
        return 'error' not in result
    
    def next(self) -> bool:
        """Play next song."""
        result = self._request('POST', '/next')
        return 'error' not in result
    
    def previous(self) -> bool:
        """Play previous song."""
        result = self._request('POST', '/previous')
        return 'error' not in result
    
    # ==============================================================================
    # QUEUE MANAGEMENT
    # ==============================================================================
    
    def add_to_queue(self, song: Union[Dict, str]) -> bool:
        """Add song to queue."""
        if isinstance(song, dict):
            song = song.get('name', song.get('file_location', ''))
        result = self._request('POST', '/queue/add', {'song': song})
        pretty(result)
        return result
    
    def remove_from_queue(self, index: int) -> bool:
        """Remove song at index from queue."""
        result = self._request('POST', '/queue/remove', {'index': index})
        return 'error' not in result
    
    def clear_queue(self) -> bool:
        """Clear the queue."""
        result = self._request('POST', '/queue/clear')
        return 'error' not in result
    
    def get_queue(self) -> List[Dict]:
        """Get current queue."""
        result = self._request('GET', '/queue')
        return result.get('queue', [])
    
    # ==============================================================================
    # VOLUME CONTROLS
    # ==============================================================================
    
    def set_volume(self, level: int) -> bool:
        """Set volume (0-100)."""
        result = self._request('POST', '/volume', {'level': level})
        return 'error' not in result
    
    def volume_up(self, amount: int = 10) -> bool:
        """Increase volume."""
        result = self._request('POST', '/volume/up')
        return 'error' not in result
    
    def volume_down(self, amount: int = 10) -> bool:
        """Decrease volume."""
        result = self._request('POST', '/volume/down')
        return 'error' not in result
    
    def mute(self) -> bool:
        """Toggle mute."""
        result = self._request('POST', '/mute')
        return 'error' not in result
    
    def unmute(self) -> bool:
        """Toggle mute (same as mute)."""
        return self.mute()
    
    def toggle_mute(self) -> bool:
        """Toggle mute."""
        return self.mute()
    
    # ==============================================================================
    # PLAYBACK SETTINGS
    # ==============================================================================
    
    def seek(self, seconds: float) -> bool:
        """Seek to position in seconds."""
        result = self._request('POST', '/seek', {'position': seconds})
        return 'error' not in result
    
    def set_repeat(self, mode: str) -> bool:
        """Set repeat mode: 'off', 'one', 'all'."""
        result = self._request('POST', '/repeat', {'mode': mode})
        return 'error' not in result
    
    def set_shuffle(self, enabled: bool) -> bool:
        """Enable/disable shuffle."""
        result = self._request('POST', '/shuffle', {'enabled': enabled})
        return 'error' not in result
    
    # ==============================================================================
    # PLAYLIST MANAGEMENT (ENHANCED)
    # ==============================================================================
    
    def create_playlist(self, name: str, songs: Optional[List] = None) -> Dict:
        """Create a new playlist. Returns response dict."""
        result = self._request('POST', '/playlist/create', {'name': name, 'songs': songs or []})
        if 'error' not in result:
            print(f"✓ Created playlist '{name}'")
        else:
            print(f"✗ Error creating playlist: {result['error']}")
        return result
        
    def delete_playlist(self, name: str) -> bool:
        """Delete a playlist."""
        result = self._request('POST', '/playlist/delete', {'name': name})
        return 'error' not in result
    
    def add_to_playlist(self, playlist_name: str, song: Union[Dict, str]) -> Dict:
        """Add a song to a playlist. Returns response dict."""
        
        if isinstance(song, dict):
            song = song.get('name', song.get('file_location', ''))
            
        playlist_id = get_playlist_id(playlist_name)
        if is_song_in_playlist(playlist_id, song): #type: ignore
            print("Already in playlist!")
            return {'status': 'already_exists'}
        else:
            print("Adding to playlist…")
            result = self._request('POST', '/playlist/add_song', {'playlist': playlist_name, 'song': song})
            if 'error' not in result:
                print(f"✓ Added '{song}' to '{playlist_name}'")
            else:
                print(f"✗ Error adding song: {result['error']}")

        return result

    def play_playlist(self, name: str) -> Dict:
        """Play a playlist. Returns response dict."""
        result = self._request('POST', '/playlist/play', {'name': name})
        if 'error' not in result:
            print(f"✓ Playing playlist '{name}'")
        else:
            print(f"✗ Error playing playlist: {result['error']}")

        return result
    
    def remove_from_playlist(self, playlist_name: str, index: int) -> bool:
        """Remove a song from a playlist by index."""
        result = self._request('POST', '/playlist/remove_song', {'playlist': playlist_name, 'index': index})
        return 'error' not in result
    
    def reorder_playlist(self, playlist_name: str, from_index: int, to_index: int) -> bool:
        """Reorder songs in a playlist."""
        result = self._request('POST', '/playlist/reorder', {
            'playlist': playlist_name,
            'from_index': from_index,
            'to_index': to_index
        })
        return 'error' not in result
    
    def rename_playlist(self, old_name: str, new_name: str) -> bool:
        """Rename a playlist."""
        result = self._request('POST', '/playlist/rename', {'old_name': old_name, 'new_name': new_name})
        return result
    
    def duplicate_playlist(self, playlist_name: str, new_name: Optional[str] = None) -> bool:
        """Duplicate a playlist."""
        data = {'playlist': playlist_name}
        if new_name:
            data['new_name'] = new_name
        result = self._request('POST', '/playlist/duplicate', data)
        return 'error' not in result
    
    def get_playlist(self, name: str) -> Dict:
        """Get details of a specific playlist."""
        result = self._request('GET', f'/playlist/{name}')
        return result
    
    def get_playlists(self) -> Dict:
        """Get all playlists."""
        result = self._request('GET', '/playlists')
        return result
    
    # ==============================================================================
    # SEARCH & INFO
    # ==============================================================================
    
    def search_songs(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for songs in the database."""
        result = self._request('GET', '/search', params={'q': query, 'limit': limit})
        return result.get('results', [])
    
    def get_status(self) -> Dict:
        """Get complete player status."""
        return self._request('GET', '/status')
    
    def get_current_song_info(self) -> Optional[Dict]:
        """Get current song info."""
        status = self.get_status()
        return status.get('current_song')
    
    def get_current_playlist(self) -> Optional[str]:
        """Get the name of the currently playing playlist."""
        status = self.get_status()
        return status.get('current_playlist')
    
    def is_playing(self) -> bool:
        """Check if player is currently playing."""
        status = self.get_status()
        return status.get('is_playing', False)

# ==============================================================================
# LEGACY COMPATIBILITY FUNCTIONS
# ==============================================================================

def play_local_file(query: str) -> bool:
    """Legacy wrapper."""
    return player.play_local(query)

def stop_playback() -> bool:
    return player.stop()

def pause_playback() -> bool:
    return player.pause()

def resume_playback() -> bool:
    return player.resume()

def get_current_player_status() -> Optional[Dict]:
    status = player.get_status()
    return {
        'is_playing': status.get('is_playing', False),
        'state': 'playing' if status.get('is_playing') else 'stopped'
    }

# ==============================================================================
# CREATE SINGLETON PLAYER CLIENT
# ==============================================================================

player = MusicPlayer()

# ==============================================================================
# CONVENIENCE FUNCTIONS
# ==============================================================================

def quick_play(query: str) -> bool:
    """Quickly play a song (search and play)."""
    return player.play_local(query)

def download_and_play(query: str, mode: str) -> bool:
    """Download audio from YouTube and play."""
    try:
        if mode == 'video':
            info = download_video(query, use_search=True)
        else:
            info = download_audio(query, use_search=True)  # Changed from download_video to download_audio
        if 'file_path' in info:
            return player.play_local(info['file_path'])
    except Exception as e:
        print(f"Error: {e}")
    return False

def create_playlist_from_search(playlist_name: str, search_query: str, limit: int = 10) -> bool:
    """Create a playlist from search results."""
    songs = player.search_songs(search_query, limit)
    if songs:
        return player.create_playlist(playlist_name, songs)
    return False

def download_and_add_to_playlist(playlist_name: str, youtube_query: str) -> bool:
    """Download a song from YouTube and add it to a playlist."""
    try:
        info = download_video(youtube_query, use_search=True)
        if 'file_path' in info:
            song_name = info.get('title', os.path.basename(info['file_path']))
            return player.add_to_playlist(playlist_name, song_name)
    except Exception as e:
        print(f"Error: {e}")
    return False




    