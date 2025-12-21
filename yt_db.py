"""Database helpers for registering downloaded music/video into Jarvis DB.

This module keeps DB interactions separate. It provides helper functions to
ensure the `music` table exists and to insert a new music entry.

Dependencies: none (uses stdlib sqlite3). For extracting media metadata,
we attempt to use `mutagen` (pip install mutagen); if it's not available
we fall back to a lightweight ffprobe call (ffmpeg must be installed).
"""
from difflib import SequenceMatcher
import sqlite3
import json
import os
from typing import Optional, Dict
from dotenv import dotenv_values
from dotenv import dotenv_values




env_vars = dotenv_values(".env")
DB_PATH = env_vars.get("DB_PATH")



def get_conn(db_path: str = DB_PATH ) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    return conn


def ensure_table(db_path: str = DB_PATH ) -> None:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS music (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        metadata TEXT,
        singer TEXT,
        cinema TEXT,
        album TEXT,
        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        duration INTEGER,
        file_location TEXT,
        genre TEXT,
        rating INTEGER
    )
    ''')
    conn.commit()
    conn.close()


def _make_json_safe(obj):
    """Recursively filter a dict to remove non-JSON-serializable objects."""
    if isinstance(obj, dict):
        safe = {}
        for k, v in obj.items():
            try:
                # test if this value is JSON serializable
                json.dumps(v)
                safe[k] = v
            except (TypeError, ValueError):
                # skip non-serializable fields (postprocessors, etc.)
                pass
        return safe
    return obj


def add_music_entry(
    file_location: str,
    name: Optional[str] = None,
    metadata: Optional[Dict] = None,
    singer: Optional[str] = None,
    cinema: Optional[str] = None,
    album: Optional[str] = None,
    duration: Optional[int] = None,
    genre: Optional[str] = None,
    rating: Optional[int] = None,
    db_path: str = DB_PATH ,
) -> int:
    """Insert a record into the `music` table. Returns the inserted row id.
    
    Prevents duplicate entries by checking if the file_location already exists.
    If it does, returns the existing id without re-inserting.
    """
    ensure_table(db_path)
    conn = get_conn(db_path)
    cur = conn.cursor()
    # store absolute path for consistency
    file_location = os.path.abspath(file_location)

    # Check if this file is already in the database
    cur.execute("SELECT id FROM music WHERE file_location = ? LIMIT 1", (file_location,))
    existing = cur.fetchone()
    if existing:
        conn.close()
        return existing[0]  # Return existing id, skip duplicate insert

    # filter metadata to only include JSON-serializable fields
    safe_metadata = _make_json_safe(metadata or {})

    cur.execute(
        """
        INSERT INTO music (name, metadata, singer, cinema, album, duration, file_location, genre, rating)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name or os.path.basename(file_location),
            json.dumps(safe_metadata),
            singer,
            cinema,
            album,
            duration,
            file_location,
            genre,
            rating,
        ),
    )
    conn.commit()
    rowid = cur.lastrowid
    conn.close()
    return rowid


def find_by_path(file_location: str, db_path: str = DB_PATH ) -> Optional[Dict]:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM music WHERE file_location = ?", (file_location,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    cols = [d[0] for d in cur.description] if cur.description else []
    return dict(zip(cols, row))


def get_media_info(file_path: str) -> Dict:
    """Try to extract basic media metadata: duration (seconds) and tags.

    Uses `mutagen` when available, otherwise tries `ffprobe` as a fallback.
    Returns a dict with at least `duration` (int seconds) and `tags` (dict).
    """
    info = {'duration': None, 'tags': {}}
    try:
        from mutagen import File as MutagenFile

        m = MutagenFile(file_path, easy=True)
        if m is not None:
            # duration in seconds
            dur = getattr(m.info, 'length', None)
            if dur:
                info['duration'] = int(dur)
            # tags as simple mapping
            tags = {}
            for k, v in (m.tags or {}).items():
                # mutagen tags may be lists
                tags[k] = v[0] if isinstance(v, (list, tuple)) else v
            info['tags'] = tags
            return info
    except Exception:
        pass

    # fallback to ffprobe
    try:
        import subprocess, shlex

        cmd = f'ffprobe -v error -show_entries format=duration:format_tags -of json "{file_path}"'
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if p.returncode == 0 and p.stdout:
            j = json.loads(p.stdout)
            fmt = j.get('format', {})
            dur = fmt.get('duration')
            if dur:
                try:
                    info['duration'] = int(float(dur))
                except Exception:
                    info['duration'] = None
            tags = fmt.get('tags') or {}
            info['tags'] = tags
    except Exception:
        pass

    return info

# for playlist db
def show_playlist_duplicates(playlist_name: str, db_path: str = DB_PATH ) -> int:
    """
    Finds duplicates in a specific playlist based on 'song_data'.
    Prints the name of the song and how many extra copies exist.
    Returns total number of duplicates found.
    """
    conn = get_conn(db_path)
    cur = conn.cursor()

    # 1. Get Playlist ID
    pid = get_playlist_id(playlist_name)
    if not pid:
        print(f"Playlist '{playlist_name}' not found.")
        conn.close()
        return 0

    # 2. Find duplicates: Group by song_data where count > 1
    cur.execute("""
        SELECT song_data, COUNT(*) 
        FROM playlist_songs 
        WHERE playlist_id = ? 
        GROUP BY song_data 
        HAVING COUNT(*) > 1
    """, (pid,))

    rows = cur.fetchall()
    total_duplicates = 0

    print(f"--- Scanning duplicates for playlist: {playlist_name} ---")

    for row in rows:
        raw_json = row[0]
        count = row[1]
        extras = count - 1 # We keep 1, so the rest are duplicates
        total_duplicates += extras
        
        # Parse JSON to get the readable name
        try:
            data = json.loads(raw_json)
            song_name = data.get("name", "Unknown Name")
        except:
            song_name = "Corrupted Data"

        print(f"• Found {extras} extra cop{'y' if extras == 1 else 'ies'} of: {song_name}")

    if total_duplicates == 0:
        print("No duplicates found.")
    
    conn.close()
    return total_duplicates

def remove_playlist_duplicates(playlist_name: str, db_path: str = DB_PATH ) -> int:
    """
    Removes duplicate songs from a specific playlist.
    Matches strict equality on 'song_data' string.
    Keeps the entry with the lowest ID (first added).
    """
    conn = get_conn(db_path)
    cur = conn.cursor()

    # 1. Get Playlist ID
    pid = get_playlist_id(playlist_name)
    if not pid:
        print(f"Playlist '{playlist_name}' not found.")
        conn.close()
        return 0

    # 2. Delete duplicates strictly within this playlist ID
    # logic: Delete rows in this playlist...
    # ...where the ID is NOT the minimum ID for that specific song_data group.
    cur.execute("""
        DELETE FROM playlist_songs 
        WHERE playlist_id = ? 
        AND id NOT IN (
            SELECT MIN(id) 
            FROM playlist_songs 
            WHERE playlist_id = ? 
            GROUP BY song_data
        )
    """, (pid, pid)) # Note: pid is passed twice

    deleted_count = cur.rowcount
    conn.commit()
    conn.close()

    print(f"Successfully removed {deleted_count} duplicate songs from '{playlist_name}'.")
    return deleted_count

# for the music db
def remove_duplicates(db_path: str = DB_PATH ) -> int:
    """Remove duplicate entries from the music table.
    
    Keeps the first occurrence (lowest id) and removes later duplicates
    based on file_location. Returns the number of rows deleted.
    """
    ensure_table(db_path)
    conn = get_conn(db_path)
    cur = conn.cursor()
    
    # Find duplicates: group by file_location and keep only the one with min id
    cur.execute("""
        DELETE FROM music 
        WHERE id NOT IN (
            SELECT MIN(id) 
            FROM music 
            GROUP BY name
        )
    """)
    
    deleted_count = cur.rowcount
    conn.commit()
    conn.close()
    
    return deleted_count



def get_duplicate_count(db_path: str = DB_PATH ) -> int:
    """Count how many duplicate entries exist in the music table.
    
    Returns the number of duplicate rows (not counting the first occurrence).
    """
    ensure_table(db_path)
    conn = get_conn(db_path)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT COUNT(*) - COUNT(DISTINCT name) 
        FROM music
    """)
    
    dup_count = cur.fetchone()[0]
    conn.close()
    
    return dup_count

def remove_perticular_entry(name: str, db_path: str = DB_PATH ) -> int:
    """Remove particular entry from the music table.
    
    Returns the number of rows deleted.
    """
    ensure_table(db_path)
    conn = get_conn(db_path)
    cur = conn.cursor()
    
    cur.execute("DELETE FROM music WHERE name LIKE ?", (f"%{name}%",))
    
    deleted_count = cur.rowcount
    conn.commit()
    conn.close()
    
    return deleted_count

def get_song_from_db(name: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name, file_location, duration, genre, singer FROM music WHERE name LIKE ?", (f"%{name}%",))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "name": row[0],
        "file_location": row[1],
        "duration": row[2],
        "genre": row[3],
        "singer": row[4]
    }


def fuzzy_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def fuzzy_match(a: str, b: str, threshold: float = 0.7) -> bool:
    return fuzzy_ratio(a, b) >= threshold


def word_fallback(db_title: str, query: str) -> bool:
    """
    Second layer: ANY query word should:
    - match exactly
    - OR be substring
    - OR fuzzy match with any word in DB title
    """

    db_words = db_title.lower().split()
    q_words = query.lower().split()

    for q in q_words:
        for d in db_words:

            # exact match
            if q == d:
                return True

            # substring match (thrill in thrills)
            if q in d:
                return True

            # fuzzy match per-word (beliver → believer)
            if fuzzy_ratio(d, q) >= 0.8:
                return True

    return False


def is_song_in_playlist(playlist_id: int, song_title: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT song_data 
        FROM playlist_songs
        WHERE playlist_id = ?
    """, (playlist_id,))
    rows = cur.fetchall()
    conn.close()

    for row in rows:
        try:
            data = json.loads(row[0])
            if "title" not in data:
                continue

            db_title = data["title"]

            # Stage 1: Full fuzzy string match
            if fuzzy_match(db_title, song_title):
                return True

            # Stage 2: Word-level fallback
            if word_fallback(db_title, song_title):
                return True

        except:
            continue

    return False

def get_playlist_id(name: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM playlists WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


    
if __name__ == "__main__":
    # print(is_song_in_playlist(2, ""))
    # print(f"Removed duplicates. Current duplicate count: {show_playlist_duplicates('My playlist')}")
    # remove_playlist_duplicates("My playlist")
    print(ensure_table())
    # print(get_song_from_db("Die with a smile"))
