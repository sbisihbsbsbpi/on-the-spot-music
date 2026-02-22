# Project Music 🎵

A comprehensive music management system combining downloading, organization, and code analysis tools.

## 📦 What's Inside

### 🎧 OnTheSpot
A powerful music downloader supporting Spotify and other streaming services.
- **Location**: `onthespot/`
- **Language**: Python
- **Features**: GUI, CLI, and Web UI frontends
- **Downloads to**: `/Users/tlreddy/Music/OnTheSpot/Tracks`

### 📁 Song Arrangement Script
Automatically organizes your music library by album.
- **File**: `songs arrangement.py`
- **Function**: Moves all albums to root directory and merges duplicates
- **Safety**: Handles filename conflicts automatically

### 🌐 Library Browser
Web-based interface to browse and search your music collection.
- **File**: `on_the_spot_library.html`
- **Features**: Search, filter, and display music with metadata
- **Usage**: Open directly in any web browser

### 🔍 GitNexus
Advanced code analysis tool that builds knowledge graphs of codebases.
- **Location**: `GitNexus-main/`
- **Purpose**: Understand code structure, dependencies, and execution flows
- **Integration**: Works with Claude Code, Cursor, Windsurf, OpenCode

## 🚀 Quick Start

### 1. Download Music

```bash
cd onthespot
python3 -m pip install -r requirements.txt
python3 -m onthespot
```

### 2. Organize Your Library

⚠️ **Backup first!**

```bash
# Backup your music
cp -r "/Users/tlreddy/Music/OnTheSpot/Tracks" "/Users/tlreddy/Music/OnTheSpot/Tracks_backup"

# Run organizer
python3 "songs arrangement.py"
```

### 3. Browse Your Collection

```bash
# Open in browser
open on_the_spot_library.html
```

### 4. Analyze the Codebase

```bash
# Index the project (running in background)
npx gitnexus@latest analyze --skip-embeddings

# Query the code
npx gitnexus@latest tool query --query "download spotify"

# Check dependencies
npx gitnexus@latest tool context --name "downloader"
```

## 📚 Documentation

- **[GITNEXUS_SETUP.md](GITNEXUS_SETUP.md)** - Complete GitNexus setup and usage guide
- **[PROJECT_WORKFLOW.md](PROJECT_WORKFLOW.md)** - Detailed workflow and common tasks
- **[GitNexus-main/README.md](GitNexus-main/README.md)** - Full GitNexus documentation
- **[onthespot/README.md](onthespot/README.md)** - OnTheSpot usage instructions

## 🎯 Common Use Cases

### Understanding the Code

```bash
# Find how authentication works
npx gitnexus@latest tool query --query "authentication flow"

# See all references to a function
npx gitnexus@latest tool context --name "download_track"

# View execution flows
npx gitnexus@latest tool query --query "download process"
```

### Before Making Changes

```bash
# Check what depends on a component
npx gitnexus@latest tool impact --target "SpotifyService" --direction "upstream"

# See what your changes affect
npx gitnexus@latest tool detect_changes --scope "all"
```

### Safe Refactoring

```bash
# Rename across all files (dry run first)
npx gitnexus@latest tool rename --symbol_name "old_name" --new_name "new_name" --dry_run true

# Then apply
npx gitnexus@latest tool rename --symbol_name "old_name" --new_name "new_name"
```

## 🛠️ Project Structure

```
project music/
├── GitNexus-main/              # Code analysis tool
│   ├── gitnexus/               # CLI package
│   ├── gitnexus-web/           # Web UI
│   └── README.md
├── onthespot/                  # Music downloader
│   ├── src/onthespot/
│   │   ├── downloader.py       # Download logic
│   │   ├── gui.py              # GUI interface
│   │   ├── cli.py              # CLI interface
│   │   ├── web.py              # Web interface
│   │   └── api/                # Service APIs
│   └── requirements.txt
├── songs arrangement.py        # Album organizer
├── on_the_spot_library.html    # Music browser
├── README.md                   # This file
├── GITNEXUS_SETUP.md          # GitNexus guide
└── PROJECT_WORKFLOW.md        # Workflow guide
```

## ⚙️ Current Status

- ✅ Git repository initialized
- ✅ Documentation created
- ⏳ GitNexus analysis running (in background)
- ⏳ Ready for music downloading and organization

## 🔗 Key Components

### OnTheSpot Core Files

- **downloader.py** - Main download engine
- **accounts.py** - Account management
- **gui.py** - PyQt GUI interface
- **cli.py** - Command-line interface
- **web.py** - Web server interface
- **api/** - Service integrations (Spotify, etc.)

### Song Arrangement Logic

The script (`songs arrangement.py`):
1. Scans all artist folders
2. Collects albums with same name
3. Moves to root and merges
4. Handles duplicates with numbering
5. Cleans up empty folders

## 🎨 GitNexus Features

### 7 Analysis Tools
- `query` - Hybrid search
- `context` - Symbol references
- `impact` - Dependency analysis
- `detect_changes` - Git diff impact
- `rename` - Multi-file refactoring
- `cypher` - Graph queries
- `list_repos` - Repository discovery

### 4 Agent Skills
- Exploring - Navigate code
- Debugging - Trace issues
- Impact Analysis - Change assessment
- Refactoring - Safe restructuring

## 🔒 Privacy & Security

- ✅ All tools run locally
- ✅ No data sent to external servers
- ✅ GitNexus index stored in `.gitnexus/` (gitignored)
- ✅ OnTheSpot downloads directly from services

## 📝 Next Steps

1. **Wait for GitNexus analysis to complete** (running in background)
2. **Set up OnTheSpot** if you haven't already
3. **Test song arrangement** on a backup folder first
4. **Explore the codebase** using GitNexus tools
5. **Customize the library UI** to your preferences

## 🆘 Need Help?

- **OnTheSpot Issues**: https://github.com/justin025/onthespot/issues
- **GitNexus Docs**: See `GITNEXUS_SETUP.md`
- **Workflow Guide**: See `PROJECT_WORKFLOW.md`

## ⚠️ Important Notes

1. **Always backup** before running `songs arrangement.py`
2. **Test on small datasets** first
3. **Read the disclaimer** in `onthespot/DISCLAIMER.md`
4. **Use responsibly** - respect copyright and terms of service

---

**Made with ❤️ for music lovers and code enthusiasts**

