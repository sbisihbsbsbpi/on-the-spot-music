"""
Stealth Mode - Avoid detection when downloading from Apple Music
Simulates human-like listening behavior with delays and limits.
"""

import json
import random
import time
from datetime import datetime, date
from pathlib import Path
from .otsconfig import config
from .runtimedata import get_logger

logger = get_logger("stealth")

# Stats file location
STATS_FILE = Path.home() / '.config' / 'onthespot' / 'stealth_stats.json'


def _load_stats():
    """Load daily stats from file."""
    try:
        if STATS_FILE.exists():
            data = json.loads(STATS_FILE.read_text())
            # Reset if it's a new day
            if data.get('date') != str(date.today()):
                return _reset_stats()
            return data
    except Exception as e:
        logger.warning(f"Failed to load stealth stats: {e}")
    return _reset_stats()


def _reset_stats():
    """Reset stats for a new day."""
    return {
        'date': str(date.today()),
        'tracks_today': 0,
        'tracks_this_hour': 0,
        'hour': datetime.now().hour,
        'session_tracks': 0,
        'last_download_time': 0
    }


def _save_stats(stats):
    """Save stats to file."""
    try:
        STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATS_FILE.write_text(json.dumps(stats, indent=2))
    except Exception as e:
        logger.warning(f"Failed to save stealth stats: {e}")


def get_stealth_stats():
    """Get current stealth mode statistics."""
    stats = _load_stats()
    
    # Reset hourly count if hour changed
    current_hour = datetime.now().hour
    if stats.get('hour') != current_hour:
        stats['hour'] = current_hour
        stats['tracks_this_hour'] = 0
        _save_stats(stats)
    
    return stats


def can_download():
    """Check if we can download based on stealth settings.

    Per-hour and per-day *limits* have been disabled so you can download
    as many Apple Music tracks as you like. We still keep stealth mode
    enabled for delays and optional session breaks, but `can_download`
    will always allow the download to proceed.
    """

    # If stealth mode is disabled, always allow.
    if not config.get('stealth_mode_enabled'):
        return True, ""

    # Stealth mode enabled, but global track caps are no longer enforced.
    # We return True unconditionally; the caller in downloader.py will
    # therefore never hit the "Rate Limited" branch.
    return True, ""


def increment_download_count():
    """Increment download counters after successful download."""
    stats = get_stealth_stats()
    stats['tracks_today'] += 1
    stats['tracks_this_hour'] += 1
    stats['session_tracks'] += 1
    stats['last_download_time'] = time.time()
    _save_stats(stats)
    
    logger.debug(f"Stealth stats: {stats['tracks_this_hour']}/hr, {stats['tracks_today']}/day")
    return stats


def calculate_stealth_delay(song_duration_ms, service="apple_music"):
    """Calculate delay between Apple Music downloads.

    For Apple Music with stealth mode enabled we now use a **fixed delay**
    based on ``stealth_min_delay`` (30 seconds by default), instead of a
    variable, song-length-based delay. This makes behaviour predictable while
    still allowing you to change the delay via settings.

    For all other services or when stealth mode is disabled, this falls back
    to the global ``download_delay`` setting.
    """

    # If stealth mode is disabled or this isn't Apple Music, just use the
    # standard global download delay (defaults to 3 seconds).
    if not config.get('stealth_mode_enabled') or service != "apple_music":
        return max(config.get('download_delay', 3), 0)

    # Apple Music + stealth mode enabled: use a fixed delay.
    # ``stealth_min_delay`` defaults to 30 seconds, which becomes the
    # "default" wait time after each successfully downloaded track.
    min_delay = config.get('stealth_min_delay', 30)
    try:
        min_delay = float(min_delay)
    except (TypeError, ValueError):
        min_delay = 30

    # Never return a negative delay.
    return max(min_delay, 0)


def check_session_break():
    """
    Check if we need to take a session break.
    
    Returns:
        (needs_break, break_duration_seconds)
    """
    if not config.get('stealth_mode_enabled'):
        return False, 0
    
    stats = get_stealth_stats()
    break_threshold = config.get('stealth_session_break_tracks', 15)
    
    if stats['session_tracks'] >= break_threshold:
        # Reset session counter
        stats['session_tracks'] = 0
        _save_stats(stats)
        
        break_minutes = config.get('stealth_session_break_minutes', 5)
        # Add some randomness to break duration
        break_seconds = break_minutes * 60 * random.uniform(0.8, 1.2)
        
        return True, break_seconds
    
    return False, 0

