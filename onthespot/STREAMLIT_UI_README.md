# OnTheSpot Streamlit UI

A modern, web-based interface for OnTheSpot built with Streamlit.

## 🎉 Features

- **🔍 Search Interface** - Search for music across multiple services
- **📥 Download Queue** - Real-time download queue with progress tracking
- **⚙️ Settings** - Configure download preferences and view account status
- **ℹ️ About** - View version info, statistics, and supported services
- **🔄 Auto-Refresh** - Automatic updates for download progress
- **📊 Statistics** - Track total downloads and data usage

## 🚀 Installation

1. **Install Streamlit dependencies:**
   ```bash
   pip install streamlit>=1.30.0 streamlit-authenticator>=0.2.3
   ```

   Or install all OnTheSpot requirements:
   ```bash
   cd onthespot
   pip install -r requirements.txt
   ```

## 🎯 Usage

### Method 1: Using the shell script (Recommended - macOS/Linux)
```bash
cd onthespot
./start_streamlit.sh
```

### Method 2: Using environment variable (All platforms)
```bash
cd onthespot
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python streamlit run src/onthespot/streamlit_ui.py
```

### Method 3: Using Python launcher
```bash
cd onthespot
python3 run_streamlit.py
```

**Note:** The environment variable `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` is required to avoid protobuf compatibility issues with librespot.

The UI will automatically open in your browser at **http://localhost:8501**

## 📖 User Guide

### Search Page (🔍)
1. Enter a search term or paste a URL
2. Select content types (Tracks, Albums, Playlists, Artists)
3. Click "Search"
4. Click "Download" on any result to add it to the queue

**Supported URL formats:**
- Spotify: `https://open.spotify.com/track/...`
- YouTube Music: `https://music.youtube.com/watch?v=...`
- Apple Music: `https://music.apple.com/...`
- And more!

### Download Queue Page (📥)
- **View all downloads** with real-time progress
- **Statistics** showing total, downloading, waiting, completed, and failed items
- **Actions:**
  - 🔄 Retry Failed - Retry all failed downloads
  - 🗑️ Clear Completed - Remove completed items from queue
  - ❌ Cancel All - Cancel all waiting downloads
- **Per-item actions:**
  - Cancel waiting downloads
  - Retry failed downloads

### Settings Page (⚙️)
Configure:
- **Download Settings:**
  - Download path
  - Max download workers
  - Max queue workers
  - Audio format (MP3, OGG, FLAC, M4A)
  - Audio quality
  - Enable retry worker
- **Search Settings:**
  - Enable/disable search for different content types
  - Show/hide thumbnails
- **Account Information:**
  - View configured accounts and their status

### About Page (ℹ️)
- Version information
- Download statistics
- Supported services
- System information

## 🎨 Features

### Auto-Refresh
Enable auto-refresh in the sidebar to automatically update the download queue:
- Toggle on/off
- Adjust refresh interval (1-10 seconds)
- Only refreshes when downloads are active

### Account Management
- View active account in sidebar
- See all configured accounts in Settings
- Switch between services

## 🔧 Configuration

The Streamlit UI uses the same configuration as other OnTheSpot UIs:
- **Config file:** `~/.config/onthespot/otsconfig.json` (Linux/Mac) or `%APPDATA%\onthespot\otsconfig.json` (Windows)
- **Cache directory:** `~/.cache/onthespot/` (Linux/Mac) or `%LOCALAPPDATA%\onthespot\` (Windows)

## 🆚 Comparison with Other UIs

| Feature | Streamlit UI | Flask Web UI | PyQt6 GUI | CLI |
|---------|-------------|--------------|-----------|-----|
| **Platform** | Web Browser | Web Browser | Desktop | Terminal |
| **Setup** | Easy | Easy | Medium | Easy |
| **Real-time Updates** | ✅ Auto-refresh | ⚠️ Manual refresh | ✅ Live | ❌ |
| **Search** | ✅ | ✅ | ✅ | ✅ |
| **Download Queue** | ✅ | ✅ | ✅ | ✅ |
| **Settings UI** | ✅ | ✅ | ✅ | ❌ |
| **Account Management** | View only | ✅ Full | ✅ Full | ✅ Full |
| **Authentication** | Optional | Optional | N/A | N/A |
| **Customization** | Limited | Full | Full | N/A |

## 🐛 Troubleshooting

### Port already in use
If port 8501 is already in use, specify a different port:
```bash
streamlit run src/onthespot/streamlit_ui.py --server.port 8502
```

### Workers not starting
Make sure you have configured at least one account using the GUI or CLI first:
```bash
python3 -m onthespot.gui
```

### Import errors
Make sure you're running from the correct directory and all dependencies are installed:
```bash
cd onthespot
pip install -r requirements.txt
```

## 📝 Notes

- **First Run:** The UI will initialize all workers on first load (may take a few seconds)
- **Account Setup:** Configure accounts using the PyQt6 GUI or CLI before using Streamlit UI
- **Concurrent Use:** You can run multiple UIs simultaneously (they share the same backend)
- **Performance:** Auto-refresh may impact performance with large queues; adjust interval as needed

## 🎯 Tips

1. **Use Auto-Refresh** when actively downloading to see real-time progress
2. **Disable Auto-Refresh** when browsing settings to prevent interruptions
3. **Clear Completed Items** regularly to keep the queue manageable
4. **Use URL Search** for quick downloads without browsing

## 📚 Additional Resources

- [OnTheSpot GitHub](https://github.com/justin025/onthespot)
- [Streamlit Documentation](https://docs.streamlit.io)
- [OnTheSpot Installation Guide](docs/INSTALLATION.md)
- [OnTheSpot Usage Guide](docs/USAGE.md)

## ⚠️ Disclaimer

OnTheSpot is intended for personal use only. Please respect copyright laws and the terms of service of the music platforms you use. Only download content you have the right to access.

