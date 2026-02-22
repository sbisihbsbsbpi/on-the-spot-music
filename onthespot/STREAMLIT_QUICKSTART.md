# OnTheSpot Streamlit UI - Quick Start Guide

Get started with the OnTheSpot Streamlit UI in 3 easy steps!

## 📦 Step 1: Install Dependencies

```bash
cd onthespot
pip install -r requirements.txt
```

This will install Streamlit and all other required dependencies.

## 🔑 Step 2: Configure an Account (First Time Only)

Before using the Streamlit UI, you need to configure at least one music service account.

**Option A: Use the GUI (Recommended)**
```bash
cd onthespot/src
python3 -m onthespot.gui
```

Then:
1. Go to the "Accounts" tab
2. Select a service (e.g., Spotify, YouTube Music)
3. Enter your credentials
4. Click "Add Account"

**Option B: Use the CLI**
```bash
cd onthespot/src
python3 -m onthespot.cli --add-account
```

## 🚀 Step 3: Launch Streamlit UI

**Option A: Using the shell script (Recommended - macOS/Linux)**
```bash
cd onthespot
./start_streamlit.sh
```

**Option B: Using environment variable (All platforms)**
```bash
cd onthespot
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python streamlit run src/onthespot/streamlit_ui.py
```

**Option C: Using Python launcher**
```bash
cd onthespot
python3 run_streamlit.py
```

The UI will open automatically in your browser at **http://localhost:8501**

## 🎵 Start Downloading!

### Quick Download (URL Method)
1. Go to the **Search** page
2. Paste a music URL (e.g., from Spotify, YouTube Music)
3. Click "Search"
4. The track/album/playlist will be added to the download queue automatically!

### Search Method
1. Go to the **Search** page
2. Enter a search term (e.g., "Bohemian Rhapsody")
3. Select content types (Tracks, Albums, etc.)
4. Click "Search"
5. Click "Download" on any result

### Monitor Downloads
1. Go to the **Download Queue** page
2. Watch real-time progress
3. Enable "Auto-Refresh" in the sidebar for live updates

## 🎯 Pro Tips

- **Enable Auto-Refresh** in the sidebar to see download progress in real-time
- **Use URL search** for fastest downloads - just paste and go!
- **Configure settings** in the Settings page to customize download quality and format
- **Multiple UIs** - You can use the Streamlit UI alongside the GUI or Flask UI

## 🆘 Need Help?

- Check the full [Streamlit UI README](STREAMLIT_UI_README.md)
- Visit the [OnTheSpot GitHub](https://github.com/justin025/onthespot)
- Read the [Installation Guide](docs/INSTALLATION.md)

## 🎉 You're All Set!

Enjoy downloading music with the modern Streamlit interface! 🎵

