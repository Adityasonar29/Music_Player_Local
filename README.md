🎵 Jarvis Music Player - Complete Media Management System

A professional, full-featured music player system with YouTube integration, playlist management, and a modern web interface. Built with Python, Flask, SQLite, and VLC.

## 🚀 Features

### 🎧 Core Music Player

- **Local Library Management** - Automatically catalog downloaded music/videos
- **VLC Integration** - High-quality audio/video playback
- **Playback Controls** - Play, pause, seek, volume, shuffle, repeat modes
- **Queue Management** - Dynamic song queue with real-time updates

### 📱 Modern Web Interface

- **Spotify-like UI** - Clean, dark/light theme interface
- **Real-time Updates** - Live playback status and progress
- **Responsive Design** - Works on desktop and mobile
- **Keyboard Shortcuts** - Space, arrows, N/P for navigation

### 🎬 YouTube Integration

- **Smart Search** - Search and download from YouTube
- **Format Options** - Download as MP3 (audio) or MP4/MKV (video)
- **Auto-registration** - Downloaded content automatically added to library
- **Cookie Support** - Handle age-restricted/region-locked content

### 📚 Database & Library

- **SQLite Database** - Reliable local storage
- **Duplicate Detection** - Smart duplicate prevention and cleanup
- **Metadata Extraction** - Automatically extract duration, artist, genre
- **Fuzzy Search** - Intelligent song matching

### 🎮 CLI Interface

- **Rich Terminal UI** - Colorful, formatted output with progress bars
- **Complete Control** - All features accessible via command line
- **Server Management** - Start/stop server, toggle settings
- **Batch Operations** - Bulk playlist and library management

### 🔄 Playlist System

- **Create/Edit Playlists** - Unlimited custom playlists
- **Smart Duplication** - Avoid duplicate songs in playlists
- **Playlist Sharing** - Export/import playlist data
- **Reorder Songs** - Drag-and-drop style reordering

## 📦 Project Structure

```
Jarvis_Music_Player/
├── music_server.py          # Main Flask server with VLC engine
├── ply_yt_2.py             # YouTube client & player interface
├── yt_db.py               # Database operations & helpers
├── music_cli.py           # Command-line interface
├── spotify_music_player.html # Web interface
├── cleanup_duplicates.py   # Database maintenance
├── requirements.txt       # Python dependencies
└── .env                  # Environment configuration
└── bin
    ├── musicplayer.bat        # Windows launcher script
```

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.8+
- VLC Media Player (install from [videolan.org](https://www.videolan.org/))
- FFmpeg (for audio processing)
- Node.js (optional, for enhanced features)

### Step 1: Clone & Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd Jarvis_Music_Player

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

Create a `.env` file in the project root:

```env
# Database configuration
DB_PATH=E:/path/to/your/music_library.db

# Server configuration
MUSIC_SERVER_URL=http://localhost:5555

# VLC settings (optional)
SHOW_VLC_DISPLAY=1  # Set to 0 to hide VLC window
```

### Step 3: First-Time Setup

```bash
# Initialize the database
python -c "from yt_db import ensure_table; ensure_table()"

# Test the server
python music_server.py
```

## 🎮 Usage

### Starting the System

```bash
# Method 1: Use the CLI (recommended)
python music_cli.py

# Method 2: Start server manually
python music_server.py

# Method 3: Use Windows launcher
musicplayer.bat
```

### Web Interface

1. Start the server: `python music_server.py`
2. Open browser to: `http://localhost:5555`
3. Or open `spotify_music_player.html` directly

## 📋 **Important: Environment Setup for CLI Access**

### ⚠️ **Adding to System PATH (Required for CLI)**

To use the music player commands from anywhere in your terminal, you need to add the project's bin folder to your system's PATH environment variable.

### **Step-by-Step Instructions:**

#### **Windows Users:**

1. **Find Your Project Path:**

   ```bash
   # In the project directory, run:
   echo %CD%
   # This will show something like: C:\Users\USER\Projects\python_projects\moduler_musicplayer
   ```
2. **Add to System PATH:**

   - Open **System Properties** (Win + Pause/Break)
   - Click **Advanced system settings**
   - Click **Environment Variables**
   - Under **System variables**, find and select **Path**, then click **Edit**
   - Click **New** and add: `C:\Users\USER\Projects\python_projects\moduler_musicplayer`
   - Click **OK** on all windows
3. **Alternative: Quick Setup via Command Line (Admin required):**

   ```cmd
   :: Run as Administrator
   setx /M PATH "%PATH%;C:\Users\USER\Projects\python_projects\moduler_musicplayer"
   ```
4. **Verify the Setup:**

   ```cmd
   :: Open a NEW command prompt and test
   musicplayer --help
   ```

#### **Linux/Mac Users:**

1. **Find Your Project Path:**

   ```bash
   pwd
   # Example output: /home/user/Projects/python_projects/moduler_musicplayer
   ```
2. **Add to PATH in your shell profile:**

   ```bash
   # For bash users (~/.bashrc or ~/.bash_profile)
   echo 'export PATH="$PATH:/home/user/Projects/python_projects/moduler_musicplayer"' >> ~/.bashrc

   # For zsh users (~/.zshrc)
   echo 'export PATH="$PATH:/home/user/Projects/python_projects/moduler_musicplayer"' >> ~/.zshrc

   # For fish users
   set -U fish_user_paths /home/user/Projects/python_projects/moduler_musicplayer $fish_user_paths
   ```
3. **Reload your shell configuration:**

   ```bash
   # For bash
   source ~/.bashrc

   # For zsh
   source ~/.zshrc
   ```
4. **Verify the Setup:**

   ```bash
   # Test from any directory
   musicplayer --help
   ```

#### **Windows Users (Alternative - Create a Shortcut):**

If you don't want to modify PATH, create a desktop shortcut:

1. **Right-click on desktop** → New → Shortcut
2. **Location:**
   ```
   "C:\Users\USER\Projects\python_projects\moduler_musicplayer\musicplayer.bat"
   ```
3. **Name it:** "Jarvis Music Player"
4. **Double-click to run**

### **Troubleshooting PATH Issues:**

#### **If commands don't work after adding to PATH:**

1. **Restart your terminal/command prompt**
2. **Verify the path is correct:**

   ```bash
   # Windows
   echo %PATH%

   # Linux/Mac
   echo $PATH
   ```
3. **Check if the batch file is executable (Linux/Mac):**

   ```bash
   chmod +x musicplayer.bat
   chmod +x music_cli.py
   ```
4. **Test directly with Python:**

   ```bash
   # Navigate to project folder and run
   python music_cli.py --help
   ```

### **Quick Test Commands:**

Once PATH is set up, you should be able to run these from **any directory**:

```bash
# Windows/Linux/Mac
musicplayer play "believer"
musicplayer status
musicplayer server start
```

### **Creating Desktop Shortcuts (Optional):**

#### **Windows Desktop Shortcut:**

1. Create a new text file on desktop called `Music Player.bat`
2. Add this content:
   ```batch
   @echo off
   cd /d "C:\Users\USER\Projects\python_projects\moduler_musicplayer"
   call "C:\Users\USER\Projects\python_projects\.venv\Scripts\activate.bat"
   python music_cli.py
   pause
   ```
3. Change the paths to match your setup
4. Save and double-click

#### **Linux Desktop Entry:**

Create `~/.local/share/applications/jarvis-music.desktop`:

```ini
[Desktop Entry]
Name=Jarvis Music Player
Comment=Music Player with YouTube Integration
Exec=/home/user/Projects/python_projects/moduler_musicplayer/venv/bin/python /home/user/Projects/python_projects/moduler_musicplayer/music_cli.py
Icon=/home/user/Projects/python_projects/moduler_musicplayer/icon.png
Terminal=true
Type=Application
Categories=AudioVideo;Player;
```

### **Adding to System PATH via Python (Automatic Setup):**

We've included a setup script to help automate this:

```bash
# Run this from the project folder
python setup_path.py
```

*Note: The setup script will guide you through the process and may require administrator privileges.*

---

**⚠️ Security Note:** Only add trusted folders to your PATH. The music player folder should be safe as it only contains your personal music files and scripts.

**Next Steps:** After setting up PATH, continue with the installation instructions below.

---

### Command Line Interface

```bash
# Play a song
python music_cli.py play "song name"

# Search and download
python music_cli.py download "artist - song" --video

# Manage playlists
python music_cli.py playlist create "My Favorites"
python music_cli.py playlist add "My Favorites" "song name"

# Control playback
python music_cli.py pause
python music_cli.py vol 80
python music_cli.py next

# Server management
python music_cli.py server start --no-display
python music_cli.py server toggle-display
```

### Python API

```python
from ply_yt_2 import player, search_youtube, download_audio

# Play a song
player.play_local("believer")

# Control playback
player.pause()
player.set_volume(80)
player.next()

# YouTube operations
results = search_youtube("coldplay yellow", max_results=5)
download_audio("coldplay yellow", use_search=True)

# Playlist management
player.create_playlist("Road Trip")
player.add_to_playlist("Road Trip", "summer hits")
player.play_playlist("Road Trip")
```

## 🔧 API Endpoints

### Server Endpoints (Port 5555)

- `GET /status` - Current player status
- `POST /play` - Play a song
- `POST /pause`, `/resume`, `/stop` - Playback controls
- `GET /search?q=query` - Search library
- `GET /youtube/search?q=query` - Search YouTube
- `POST /youtube/download` - Download from YouTube
- `GET /playlists` - List all playlists
- `POST /playlist/create` - Create new playlist
- `GET /playlist/{name}` - Get playlist details

### WebSocket Events

- `status_update` - Player status changes
- `queue_update` - Queue modifications
- `library_update` - Library changes

## 🗃️ Database Schema

### Music Table

```sql
CREATE TABLE music (
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
```

### Playlists Table

```sql
CREATE TABLE playlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

CREATE TABLE playlist_songs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    playlist_id INTEGER NOT NULL,
    song_data TEXT NOT NULL,
    position INTEGER NOT NULL,
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

## 🔄 Integration Examples

### Integrate like

```python
# In your Jarvis main script
from ply_yt_2 import player

def play_music(song_name):
    """Play music from command """
    response = player.play_local(song_name)
    if 'error' in response:
        return f"Couldn't find {song_name}"
    return f"Playing {song_name}"

def download_from_youtube(query):
    """Download music from YouTube """
    from ply_yt_2 import download_audio
    info = download_audio(query, use_search=True)
    return f"Downloaded {info.get('title')}"
```

### Scheduled Library Maintenance

```python
# Add to cron job or scheduled task
from cleanup_duplicates import main as cleanup
from yt_db import remove_duplicates

# Weekly cleanup
cleanup()
remove_duplicates()
```

## 🎨 Web Interface Features

### Keyboard Shortcuts

- **Space** - Play/Pause
- **← →** - Seek forward/backward
- **↑ ↓** - Volume up/down
- **N** - Next song
- **P** - Previous song
- **Q** - Toggle queue panel

### Themes

- **Dark Mode** - Default, eye-friendly
- **Light Mode** - Bright theme option
- **Auto-save** - Remembers your preference

### Responsive Design

- **Desktop** - Full feature set, multi-panel layout
- **Tablet** - Adaptive layout, touch-friendly
- **Mobile** - Simplified controls, mobile-optimized

## 🛡️ Error Handling & Recovery

### Common Issues & Solutions

1. **"VLC not found"**

   - Install VLC Media Player
   - Add VLC to system PATH
   - Restart the application
2. **"Server not responding"**

   ```bash
   python music_cli.py server restart
   # Or manually:
   ps aux | grep music_server
   kill -9 <PID>
   python music_server.py
   ```
3. **"Database locked"**

   ```bash
   # Check for other processes
   fuser music_library.db
   # Or restart the system
   python music_cli.py server restart
   ```
4. **"YouTube download failing"**

   - Update yt-dlp: `pip install --upgrade yt-dlp`
   - Check internet connection
   - Update cookies file for age-restricted content

## 📊 Performance Tips

### For Large Libraries

```python
# Optimize database
from yt_db import get_conn
conn = get_conn()
conn.execute("PRAGMA synchronous = OFF")
conn.execute("PRAGMA journal_mode = MEMORY")
conn.close()
```

### Memory Management

- Server automatically caches recent songs
- Queue limited to 1000 songs
- History tracks last 50 played songs

## 🔗 Dependencies

### Core

- `python-vlc` - VLC media player integration
- `Flask` - Web server framework
- `yt-dlp` - YouTube downloading
- `mutagen` - Audio metadata extraction

### UI & CLI

- `rich` - Terminal formatting
- `typer` - CLI framework
- `requests` - HTTP client

### Database

- `sqlite3` - Built-in database
- `python-dotenv` - Configuration management

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt
pip install pytest black flake8

# Run tests
pytest tests/

# Code formatting
black .
flake8 .
```

## 📄 License

MIT License - See LICENSE file for details.

## 🆘 Support & Community

- **Issues**: Report bugs on GitHub Issues
- **Discussions**: Feature requests and questions
- **Contributing**: Pull requests welcome

## 🚨 Security Notes

- Never commit `.env` file with sensitive data
- Use local database, no cloud credentials required
- YouTube downloads respect copyright laws
- All processing happens locally on your machine

---

**Enjoy your music!** 🎶

For more information, check the source code documentation or open an issue for support.
