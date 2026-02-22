# Project Music - Workflow Guide

## Overview

This project combines music downloading, organization, and analysis tools:

1. **OnTheSpot** - Downloads music from Spotify and other services
2. **songs arrangement.py** - Organizes downloaded music by album
3. **on_the_spot_library.html** - Browse your music collection
4. **GitNexus** - Analyze and understand the codebase

## Typical Workflow

### 1. Download Music with OnTheSpot

```bash
cd onthespot
python3 -m pip install -r requirements.txt
python3 -m onthespot
```

This will:
- Launch the OnTheSpot GUI
- Allow you to search and download music
- Save files to `/Users/tlreddy/Music/OnTheSpot/Tracks`

### 2. Organize Your Music Library

After downloading, run the organization script:

```bash
python3 "songs arrangement.py"
```

This script:
- Collects all albums from artist folders
- Moves albums to the root Tracks directory
- Merges duplicate albums
- Handles filename conflicts
- Removes empty artist folders

**Before:**
```
Tracks/
├── Artist A/
│   ├── Album 1/
│   └── Album 2/
└── Artist B/
    └── Album 1/
```

**After:**
```
Tracks/
├── Album 1/  (merged from both artists)
└── Album 2/
```

### 3. Browse Your Library

Open `on_the_spot_library.html` in your browser to:
- View all your downloaded music
- Search and filter tracks
- See album artwork and metadata
- Play music directly from the browser

### 4. Analyze Code with GitNexus

To understand or modify the codebase:

```bash
# Index the project
npx gitnexus@latest analyze

# Query specific functionality
npx gitnexus@latest tool query --query "download track spotify"

# Check impact before making changes
npx gitnexus@latest tool impact --target "download_function" --direction "upstream"
```

## Common Tasks

### Add New Music Service to OnTheSpot

1. Use GitNexus to understand the architecture:
   ```bash
   npx gitnexus@latest tool query --query "service integration"
   ```

2. Check what depends on existing services:
   ```bash
   npx gitnexus@latest tool context --name "SpotifyService"
   ```

3. Make your changes

4. Check impact:
   ```bash
   npx gitnexus@latest tool detect_changes --scope "all"
   ```

### Modify Song Organization Logic

1. View the current script:
   ```bash
   cat "songs arrangement.py"
   ```

2. Before editing, check if it's used elsewhere:
   ```bash
   npx gitnexus@latest tool context --name "album_map"
   ```

3. Make changes and test on a backup folder first!

### Customize the Library UI

1. Open `on_the_spot_library.html` in your editor

2. The file is self-contained with inline CSS and JavaScript

3. Test changes by opening in browser

## Safety Tips

### Before Running songs arrangement.py

⚠️ **IMPORTANT**: This script moves files! Always:

1. **Backup your music folder first**:
   ```bash
   cp -r "/Users/tlreddy/Music/OnTheSpot/Tracks" "/Users/tlreddy/Music/OnTheSpot/Tracks_backup"
   ```

2. **Test on a small subset** by modifying `BASE_DIR` temporarily

3. **Review the script** to understand what it does

### Before Modifying OnTheSpot

1. Create a git branch:
   ```bash
   cd onthespot
   git checkout -b my-feature
   ```

2. Use GitNexus to understand dependencies

3. Test thoroughly before using on your main library

## Project Structure

```
project music/
├── GitNexus-main/          # Code analysis tool
│   ├── gitnexus/           # CLI package
│   ├── gitnexus-web/       # Web UI
│   └── README.md           # Full documentation
├── onthespot/              # Music downloader
│   ├── src/                # Source code
│   ├── requirements.txt    # Python dependencies
│   └── README.md           # Usage instructions
├── songs arrangement.py    # Album organizer script
├── on_the_spot_library.html # Music browser UI
├── GITNEXUS_SETUP.md       # GitNexus setup guide
└── PROJECT_WORKFLOW.md     # This file
```

## Useful Commands

### OnTheSpot
```bash
# Install
python3 -m pip install git+https://github.com/justin025/onthespot

# Run GUI
python3 -m onthespot

# Run CLI
python3 -m onthespot --cli
```

### GitNexus
```bash
# Analyze project
npx gitnexus@latest analyze

# Setup MCP for editors
npx gitnexus@latest setup

# List indexed repos
npx gitnexus@latest list

# Check status
npx gitnexus@latest status

# Generate wiki
npx gitnexus@latest wiki
```

### Git
```bash
# Check status
git status

# Create branch
git checkout -b feature-name

# Commit changes
git add .
git commit -m "Description"
```

## Next Steps

1. ✅ Git repository initialized
2. ⏳ Run GitNexus analysis: `npx gitnexus@latest analyze`
3. ⏳ Set up OnTheSpot if not already done
4. ⏳ Test the song arrangement script on a backup
5. ⏳ Customize the library HTML to your preferences

## Resources

- OnTheSpot: https://github.com/justin025/onthespot
- GitNexus: https://github.com/abhigyanpatwari/gitnexus
- GitNexus Web UI: https://gitnexus.vercel.app

