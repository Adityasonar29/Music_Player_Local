"""
Jarvis Music Player CLI - Complete Edition
"""
import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
import sys
import os
import json
import requests
import time       # <-- ADD THIS
import subprocess


# Setup paths to import your local files
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import dotenv_values
env_vars = dotenv_values(".env")


try:
    import ply_yt_2 as client
    import yt_db as db
except ImportError:
    rprint("[bold red]Error:[/bold red] Could not import 'ply_yt_2' or 'yt_db'.")
    sys.exit(1)
    
# Get the server URL from the client module (assuming it's available)
try:
    SERVER_URL = client.MUSIC_SERVER_URL
except AttributeError:
    # Fallback in case MUSIC_SERVER_URL isn't explicitly exposed in ply_yt_2
    SERVER_URL = env_vars.get("MUSIC_SERVER_URL")
    print(SERVER_URL)  # debug 

# Main App and Sub-Apps
app = typer.Typer(help="Jarvis Music Player Ultimate CLI", add_completion=False)
queue_app = typer.Typer(help="Manage the song queue")
playlist_app = typer.Typer(help="Create, Edit, and Play Playlists")
db_app = typer.Typer(help="Database & Library Tools")
server_app = typer.Typer(help="Manage the music server")

app.add_typer(queue_app, name="queue")
app.add_typer(playlist_app, name="playlist")
app.add_typer(db_app, name="db")
app.add_typer(server_app, name="server")

console = Console()


# Helper function to convert seconds to MM:SS format
def format_time(seconds):
    if seconds is None:
        return "N/A"
    try:
        seconds = int(seconds)
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    except (TypeError, ValueError):
        return "N/A"
# ==============================================================================
# 🎵 MAIN PLAYBACK COMMANDS
# ==============================================================================

@app.command()
def play(song: str = typer.Argument(..., help="Song name or file path")):
    """Play a song immediately."""
    result = client.player.play_local(song)
    rprint(result)
    rprint(f"[green]▶ Playing:[/green] {song}")

@app.command()
def pause():
    """Pause playback."""
    client.player.pause()
    rprint("[yellow]⏸ Paused[/yellow]")

@app.command()
def resume():
    """Resume playback."""
    client.player.resume()
    rprint("[green]▶ Resumed[/green]")

@app.command()
def stop():
    """Stop playback."""
    client.player.stop()
    rprint("[red]◼ Stopped[/red]")

@app.command()
def next():
    """Skip to next song."""
    client.player.next()
    rprint("[cyan]⏭ Next Song[/cyan]")

@app.command()
def prev():
    """Go to previous song."""
    client.player.previous()
    rprint("[cyan]⏮ Previous Song[/cyan]")

@app.command()
def vol(level: int):
    """Set volume (0-100)."""
    client.player.set_volume(level)
    rprint(f"🔊 Volume set to [bold]{level}%[/bold]")

@app.command()
def mute():
    """Toggle Mute."""
    client.player.toggle_mute()
    rprint("🔇 Mute toggled")

@app.command()
def seek(seconds: float):
    """Seek to a specific time (in seconds)."""
    client.player.seek(seconds)
    rprint(f"⏩ Seeked to {seconds}s")

@app.command()
def shuffle(on: bool = True):
    """Turn shuffle ON or OFF."""
    client.player.set_shuffle(on)
    state = "ON" if on else "OFF"
    rprint(f"🔀 Shuffle is now [bold]{state}[/bold]")

@app.command()
def repeat(mode: str = typer.Argument(..., help="'off', 'one', or 'all'")):
    """Set repeat mode (off, one, all)."""
    client.player.set_repeat(mode)
    rprint(f"🔁 Repeat mode: [bold]{mode}[/bold]")



@app.command()
def status():
    """Show detailed player status, including position, volume, and playback state."""
    st = client.player.get_status()
    
    # --- Data Extraction and Formatting ---
    is_playing = st.get('is_playing', False)
    state = "▶ Playing" if is_playing else "⏸ Paused" if st.get('position') is not None else "◼ Stopped"
    
    current_song_data = st.get("current_song") or {}
    title = current_song_data.get("name") \
        or current_song_data.get("title", "N/A")
    artist = current_song_data.get("singer", "N/A")
    
    duration_s = st.get('duration')
    position_s = st.get('position')
    
    # Format time and progress bar
    duration_str = format_time(duration_s)
    position_str = format_time(position_s)
    
    progress_bar = ""
    if duration_s and position_s is not None and duration_s > 0:
        percent = (position_s / duration_s) * 100
        progress_char = "█"
        bar_length = 30
        filled_length = int(bar_length * percent // 100)
        bar = progress_char * filled_length + '—' * (bar_length - filled_length)
        progress_bar = f"[[green]{bar}[/green]] {position_str}/{duration_str}"
    elif is_playing:
        progress_bar = f"[yellow]{position_str}[/yellow] / {duration_str} [dim](Live/Streaming)[/dim]"


    # --- Rich Table Output ---
    
    table = Table(title="Jarvis Music Player Status", box=None, show_header=False)
    table.add_column("Property", style="cyan", width=15)
    table.add_column("Value", style="yellow")
    
    table.add_row("[bold]State[/bold]", f"{state}")
    
    # Only show song details if a song is loaded
    if title != 'N/A':
        table.add_row("[bold]Song[/bold]", f"{title}")
        table.add_row("[bold]Artist/Singer[/bold]", artist)
        
        # Add the progress bar row
        table.add_row("[bold]Progress[/bold]", progress_bar)

    table.add_section() # Visual separator
    
    table.add_row(f"\nVolume", f"\n{str(st.get('volume', 'N/A'))}%")
    table.add_row("Muted", "[red]YES[/red]" if st.get('muted', False) else "[green]NO[/green]")

    table.add_row("Shuffle", "ON" if st.get('shuffle', False) else "OFF")
    table.add_row("Repeat", st.get('repeat', 'off').upper())
    
    pl_name = st.get('current_playlist')
    if pl_name:
        table.add_row("\nPlaylist", f"\n{pl_name}")
        table.add_row("Index", str(st.get('playlist_index', 'N/A')))
        table.add_row("Queue Size", str(st.get('queue_size', 'N/A')))
    
    visible = "[green]Visible[/green]" if st.get('show_display', True) else "[red]Hidden[/red]"
    
    # Add this with the other table rows, perhaps near the Shuffle/Repeat settings
    table.add_row("\nDisplay", f"\n{visible}")
    console.print(table)

# ==============================================================================
# ⬇️ DOWNLOAD & SEARCH
# ==============================================================================

@app.command()
def download(
    query: str,
    video: bool = typer.Option(False, "--video", "-v", help="Download as Video (MKV/MP4)"),
    play: bool = typer.Option(False, "--play", "-p", help="Play immediately after download")
):
    """
    Download from YouTube. Defaults to Audio (MP3).
    Use --video for video files.
    """
    mode_str = "video" if video else "audio"
    rprint(f"[cyan]⬇ Downloading {mode_str}:[/cyan] {query}...")
    
    if play:
        client.download_and_play(query, mode=mode_str)
    else:
        if video:
            client.download_video(query, use_search=True)
        else:
            client.download_audio(query, use_search=True)
        rprint(f"[green]✓ {mode_str.capitalize()} saved to library.[/green]")

@app.command()
def search(query: str, online: bool = typer.Option(False, "--online", "-o", help="Search YouTube instead of Local DB")):
    """
    Search for songs. 
    Default: Local DB. 
    Use --online to search YouTube.
    """
    if online:
        rprint(f"[cyan]🔎 Searching YouTube for:[/cyan] {query}")
        results = client.search_youtube(query, max_results=5)
    else:
        rprint(f"[cyan]🔎 Searching Local Library for:[/cyan] {query}")
        results = client.player.search_songs(query)

    if not results:
        rprint("[red]No results found.[/red]")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Title")
    table.add_column("Details")

    for idx, item in enumerate(results, 1):
        title = item.get('title') or item.get('name')
        extra = item.get('uploader') or item.get('singer') or "Unknown"
        table.add_row(str(idx), title, extra)
    
    console.print(table)

# ==============================================================================
# 📋 QUEUE MANAGEMENT
# ==============================================================================

@queue_app.command("show")
def queue_show():
    """Show the current queue."""
    q = client.player.get_queue()
    if not q:
        rprint("[yellow]Queue is empty.[/yellow]")
        return
    
    table = Table(title="Current Queue")
    table.add_column("Index", justify="right", style="cyan", no_wrap=True)
    table.add_column("Song Name", style="magenta")
    
    for idx, song in enumerate(q):
        name = song.get('name') or song.get('title') or "Unknown"
        table.add_row(str(idx), name)
    console.print(table)

@queue_app.command("add")
def queue_add(song: str):
    """Add a song to the queue."""
    client.player.add_to_queue(song)
    rprint(f"[green]Added to queue:[/green] {song}")

@queue_app.command("remove")
def queue_remove(index: int):
    """Remove a song from queue by Index."""
    client.player.remove_from_queue(index)
    rprint(f"[yellow]Removed song at index {index}[/yellow]")

@queue_app.command("clear")
def queue_clear():
    """Clear the entire queue."""
    client.player.clear_queue()
    rprint("[red]Queue cleared.[/red]")

# ==============================================================================
# 📑 PLAYLIST MANAGEMENT
# ==============================================================================

@playlist_app.command("list")
def playlist_list():
    """List all available playlists."""
    data = client.player.get_playlists()
    playlists = data.get('playlists', {})
    
    table = Table(title="Playlists")
    table.add_column("Name", style="green")
    table.add_column("Song Count", style="white")
    
    for name, count in playlists.items():
        table.add_row(name, str(count))
    console.print(table)

@playlist_app.command("play")
def playlist_play_cmd(name: str):
    """Play an entire playlist."""
    client.player.play_playlist(name)
    rprint(f"[purple]Playing Playlist:[/purple] {name}")

@playlist_app.command("create")
def playlist_create_cmd(name: str):
    """Create a new playlist."""
    client.player.create_playlist(name)
    rprint(f"Created: {name}")

@playlist_app.command("delete")
def playlist_delete_cmd(name: str):
    """Delete a playlist."""
    client.player.delete_playlist(name)
    rprint(f"[red]Deleted: {name}[/red]")

@playlist_app.command("add")
def playlist_add_song(playlist: str, song: str):
    """Add a song to a playlist."""
    result = client.player.add_to_playlist(playlist, song)
    rprint(result)
    rprint(f"Added '{song}' to '{playlist}'")

@playlist_app.command("remove")
def playlist_remove_song(playlist: str, index: int):
    """Remove song from playlist by index."""
    client.player.remove_from_playlist(playlist, index)
    rprint(f"Removed song at {index} from '{playlist}'")

@playlist_app.command("rename")
def playlist_rename(old_name: str, new_name: str):
    """Rename a playlist."""
    client.player.rename_playlist(old_name, new_name)
    rprint(f"Renamed '{old_name}' to '{new_name}'")

@playlist_app.command("copy")
def playlist_duplicate(name: str, new_name: str = typer.Argument(None)):
    """Duplicate a playlist."""
    client.player.duplicate_playlist(name, new_name)
    rprint(f"Duplicated '{name}'")

@playlist_app.command("reorder")
def playlist_reorder(name: str, from_index: int, to_index: int):
    """Move a song from one position to another."""
    client.player.reorder_playlist(name, from_index, to_index)
    rprint(f"Moved song {from_index} -> {to_index} in '{name}'")

@playlist_app.command("show")
def playlist_show_songs(name: str):
    """List songs inside a specific playlist."""
    data = client.player.get_playlist(name)
    songs = data.get('songs', [])
    
    if not songs:
        rprint(f"[yellow]Playlist '{name}' is empty or not found.[/yellow]")
        return

    table = Table(title=f"Songs in {name}")
    table.add_column("#", style="dim")
    table.add_column("Title")
    table.add_column("Artist")

    for i, song in enumerate(songs):
        title = song.get('name', 'Unknown')
        artist = song.get('singer', '')
        table.add_row(str(i), title, artist)
    
    console.print(table)

# ==============================================================================
# 🗄️ DATABASE COMMANDS
# ==============================================================================

@db_app.command("clean")
def db_clean():
    """Remove duplicates from the entire library."""
    count = db.remove_duplicates()
    rprint(f"[green]Cleaned {count} duplicates from Library.[/green]")

@db_app.command("clean-playlist")
def db_clean_pl(name: str):
    """Remove duplicates from a specific playlist."""
    count = db.remove_playlist_duplicates(name)
    rprint(f"[green]Removed {count} duplicates from '{name}'.[/green]")

@db_app.command("count-duplicates")
def db_count():
    """Count total duplicates."""
    count = db.get_duplicate_count()
    rprint(f"Found {count} duplicates.")

@db_app.command("remove-entry")
def db_remove_entry(name: str):
    """Remove a specific song from DB permanently."""
    count = db.remove_perticular_entry(name)
    rprint(f"[red]Removed {count} entries matching '{name}'.[/red]")

@db_app.command("info")
def db_info(song: str):
    """Show raw DB info for a song."""
    data = db.get_song_from_db(song)
    if data:
        rprint(json.dumps(data, indent=2))
    else:
        rprint("[red]Not found.[/red]")

@db_app.command("list-all")
def db_list_all():
    """List all songs in the database."""
    songs = client.list_downloaded_songs()
    table = Table(title="All Downloaded Music")
    table.add_column("ID", style="dim")
    table.add_column("Name")
    table.add_column("Artist")
    
    for s in songs:
        table.add_row(str(s['id']), s['name'], str(s['singer']))
    console.print(table)

def server_check(url: str, attempts: int = 3, delay: float = 0.5) -> bool:
    """Pings the music server to ensure it's running."""
    for _ in range(attempts):
        try:
            response = requests.get(f"{url}/ping", timeout=delay)
            if response.status_code == 200 and response.json().get('status') == 'alive':
                return True
        except requests.exceptions.RequestException:
            # Server is likely not running or connection failed, try again after delay
            time.sleep(delay)
    return False

def start_server_in_background(show_display=True):
    """Starts the music_server.py as a non-blocking background process.
    
    Args:
        show_display (bool): Whether to show the VLC display window. Defaults to True.
    """
    # 1. Locate the server file. Assuming it's in the same directory.
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music_server.py")
    pid_file = os.path.join(os.path.dirname(script_path), "music_server.pid")
    
    if not os.path.exists(script_path):
        rprint(f"[bold red]FATAL ERROR:[/bold red] Cannot find server file at: [dim]{script_path}[/dim]")
        sys.exit(1)

    rprint(f"[bold yellow]Starting server...[/bold yellow] (Running: [cyan]python {os.path.basename(script_path)}[/cyan])")
    
    # 2. Prepare environment variables
    env_vars = dotenv_values(r".env")
    
    # Create a copy of the current environment and update with .env values
    env = os.environ.copy()
    env.update(env_vars)
    
    # Override SHOW_VLC_DISPLAY if explicitly provided
    if show_display is not None:
        env["SHOW_VLC_DISPLAY"] = "1" if show_display else "0"
    
    # 3. Start the server using subprocess
    if sys.platform == "win32":
        # Windows: Use CREATE_NO_WINDOW to prevent console window from showing
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        server_process = subprocess.Popen(
            [sys.executable, script_path],
            creationflags=subprocess.CREATE_NO_WINDOW,
            close_fds=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            startupinfo=startupinfo
        )
    else:
        # Linux/macOS: Use a simple non-blocking call
        server_process = subprocess.Popen(
            [sys.executable, script_path],
            preexec_fn=os.setpgrp,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env
        )
    
    # Save the PID to a file for later reference
    with open(pid_file, 'w') as f:
        f.write(str(server_process.pid))

    # 4. Wait for the server to become available
    time.sleep(2)  # Initial wait for Flask to boot
    
    if server_check(SERVER_URL, attempts=5, delay=0.5):
        rprint("[bold green]✓ Server is running. Executing command...[/bold green]")
        return True
    else:
        rprint("[bold red]FATAL ERROR:[/bold red] Server failed to start or did not become responsive.")
        return False

def stop_server_in_background():
    """Stops the music server that was started in the background.
    
    Returns:
        bool: True if server was stopped successfully, False otherwise.
    """
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music_server.py")
    pid_file = os.path.join(os.path.dirname(script_path), "music_server.pid")
    
    # Check if PID file exists
    if not os.path.exists(pid_file):
        rprint("[yellow]No server process found to stop.[/yellow]")
        return False
    
    try:
        # Read the PID from the file
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        # Try to terminate the process
        try:
            if sys.platform == "win32":
                # On Windows, use taskkill to terminate the process
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL)
            else:
                # On Unix-like systems, use os.kill
                import signal
                os.kill(pid, signal.SIGTERM)
            
            rprint(f"[green]✓ Successfully stopped server (PID: {pid})[/green]")
            return True
            
        except (ProcessLookupError, subprocess.CalledProcessError):
            rprint(f"[yellow]No running server process found with PID {pid}. The server may have already been stopped.[/yellow]")
            return False
        
    except Exception as e:
        rprint(f"[red]Error stopping server: {str(e)}[/red]")
        return False
    
    finally:
        # Always clean up the PID file
        try:
            if os.path.exists(pid_file):
                os.remove(pid_file)
        except Exception as e:
            rprint(f"[yellow]Warning: Could not remove PID file: {str(e)}[/yellow]")
            
    return False

@server_app.command("start")
def server_start(show_display: bool = typer.Option(True, help="Whether to show VLC display window")):
    """Start the music server in the background."""
    if server_check(SERVER_URL):
        rprint("[yellow]Server is already running.[/yellow]")
        return True
    
    rprint("[bold green]Starting music server...[/bold green]")
    if start_server_in_background(show_display=show_display):
        rprint("[green]✓ Music server started successfully![/green]")
        return True
    else:
        rprint("[red]Failed to start music server.[/red]")
        return False

@server_app.command("stop")
def server_stop():
    """Stop the running music server."""
    if not server_check(SERVER_URL):
        rprint("[yellow]No running server found to stop.[/yellow]")
        return False
    
    rprint("[bold yellow]Stopping music server...[/bold yellow]")
    if stop_server_in_background():
        rprint("[green]✓ Music server stopped successfully![/green]")
        return True
    else:
        rprint("[red]Failed to stop music server. It may have already been stopped.[/red]")
        return False

@server_app.command("status")
def server_status():
    """Check if the music server is running."""
    if server_check(SERVER_URL):
        rprint("[green]✓ Music server is running[/green]")
        return True
    else:
        rprint("[yellow]Music server is not running[/yellow]")
        return False

@server_app.command("toggle-display")
def toggle_display(restart: bool = typer.Option(True, help="Automatically restart server to apply changes")):
    """Toggle the VLC display setting."""
    try:
        # Get current status first
        status = requests.get(f"{SERVER_URL}/status").json()
        current = status.get('show_display', True)
        
        # Toggle the setting
        response = requests.post(f"{SERVER_URL}/display/toggle", timeout=5)
        response.raise_for_status()
        result = response.json()
        
        if 'error' in result:
            rprint(f"[red]Error: {result['error']}[/red]")
            return False
            
        rprint(f"[yellow]{result.get('message', 'Display setting updated.')}[/yellow]")
        new_setting = not current
        rprint(f"New display setting: {'[green]Visible[/green]' if new_setting else '[red]Hidden[/red]'}")
        
        # Restart server if requested
        if restart:
            rprint("[yellow]Restarting server to apply changes...[/yellow]")
            if restart_server(show_display=new_setting):
                rprint("[green]✓ Server restarted with new display setting[/green]")
            else:
                rprint("[red]Failed to restart server with new settings[/red]")
        else:
            rprint("[yellow]Please restart the server for changes to take effect.[/yellow]")
            
        return True
        
    except requests.exceptions.RequestException as e:
        rprint(f"[red]Failed to connect to music server: {e}[/red]")
        rprint(f"[yellow]Is the server running at {SERVER_URL}?[/yellow]")
        return False
    
def restart_server(show_display=None):
    """Restart the server with the current settings."""
    # Get current display setting if not provided
    if show_display is None:
        try:
            response = requests.get(f"{SERVER_URL}/status")
            if response.status_code == 200:
                show_display = response.json().get('show_display', True)
        except:
            show_display = True
    
    # Stop the server if it's running
    if server_check(SERVER_URL):
        server_stop()
    
    # Start with the specified display setting
    return server_start(show_display)

if __name__ == "__main__":
    # 1. Check if the server is already running
    if server_check(SERVER_URL):
        # Server is already running, proceed immediately
        pass 
    else:
        # 2. Server is not running, attempt to start it in the background
        rprint("\n[bold magenta]Server Not Found.[/bold magenta] Attempting to auto-start the music server...")
        if not start_server_in_background():
            sys.exit(1)
        
    # 3. Execute the user's command via Typer
    app()