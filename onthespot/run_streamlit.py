#!/usr/bin/env python3
"""
OnTheSpot Streamlit UI Launcher

This script launches the Streamlit UI for OnTheSpot.

Usage:
    python3 run_streamlit.py
"""

import os
import sys
import subprocess

# CRITICAL: Set this BEFORE launching Streamlit to avoid protobuf errors
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

# Get the path to the streamlit UI file
script_dir = os.path.dirname(os.path.abspath(__file__))
streamlit_ui_path = os.path.join(script_dir, 'src', 'onthespot', 'streamlit_ui.py')

# Launch Streamlit with the environment variable already set
if __name__ == '__main__':
    print("🎵 Launching OnTheSpot Streamlit UI...")
    print(f"📁 UI Path: {streamlit_ui_path}")
    print("🌐 The UI will open in your browser at http://localhost:8501")
    print()

    # Run streamlit with the environment variable
    subprocess.run([
        sys.executable, '-m', 'streamlit', 'run',
        streamlit_ui_path,
        '--server.headless=false'
    ], env=os.environ.copy())

