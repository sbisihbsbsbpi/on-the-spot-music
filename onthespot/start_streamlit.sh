#!/bin/bash
# OnTheSpot Streamlit UI Launcher Script
# This script sets the required environment variable and launches the Streamlit UI

# Set the environment variable to avoid protobuf errors
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Launch Streamlit
echo "🎵 Launching OnTheSpot Streamlit UI..."
echo "🌐 The UI will open in your browser at http://localhost:8501"
echo ""

cd "$SCRIPT_DIR/src"
streamlit run onthespot/streamlit_ui.py

