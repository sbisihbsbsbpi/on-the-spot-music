#!/usr/bin/env python3
"""
OnTheSpot Streamlit UI

A modern web-based interface for OnTheSpot music downloader built with Streamlit.
"""

# CRITICAL: Set this BEFORE any other imports to avoid protobuf errors
import os
import sys
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

# Now safe to import other modules
import streamlit as st
import pandas as pd
import time
import threading
import shutil

# Handle imports for both direct execution and module execution
try:
	from .accounts import FillAccountPool, get_account_token
	from .downloader import DownloadWorker, RetryWorker
	from .otsconfig import cache_dir, config_dir, config
	from .parse_item import parsingworker, parse_url
	from .runtimedata import get_logger, account_pool, pending, download_queue, download_queue_lock, pending_lock, get_queue_sizes
	from .search import get_search_results
	from .utils import format_bytes, open_item
	from .stealth import get_stealth_stats
	from .ui_theme import set_accent_color, get_colors, get_accent_color
	# Account add/login helpers (mirror Qt main UI)
	from .api.apple_music import apple_music_add_account
	from .api.bandcamp import bandcamp_add_account
	from .api.deezer import deezer_add_account
	from .api.qobuz import qobuz_add_account
	from .api.soundcloud import soundcloud_add_account
	from .api.spotify import spotify_new_session
	from .api.tidal import tidal_add_account_pt1, tidal_add_account_pt2
	from .api.youtube_music import youtube_music_add_account
	from .api.generic import generic_add_account, generic_list_extractors
	from .api.crunchyroll import crunchyroll_add_account
except ImportError:
	# If relative imports fail, try absolute imports
	from onthespot.accounts import FillAccountPool, get_account_token
	from onthespot.downloader import DownloadWorker, RetryWorker
	from onthespot.otsconfig import cache_dir, config_dir, config
	from onthespot.parse_item import parsingworker, parse_url
	from onthespot.runtimedata import get_logger, account_pool, pending, download_queue, download_queue_lock, pending_lock, get_queue_sizes
	from onthespot.search import get_search_results
	from onthespot.utils import format_bytes, open_item
	from onthespot.stealth import get_stealth_stats
	from onthespot.ui_theme import set_accent_color, get_colors, get_accent_color
	from onthespot.api.apple_music import apple_music_add_account
	from onthespot.api.bandcamp import bandcamp_add_account
	from onthespot.api.deezer import deezer_add_account
	from onthespot.api.qobuz import qobuz_add_account
	from onthespot.api.soundcloud import soundcloud_add_account
	from onthespot.api.spotify import spotify_new_session
	from onthespot.api.tidal import tidal_add_account_pt1, tidal_add_account_pt2
	from onthespot.api.youtube_music import youtube_music_add_account
	from onthespot.api.generic import generic_add_account, generic_list_extractors
	from onthespot.api.crunchyroll import crunchyroll_add_account

logger = get_logger("streamlit_ui")

# Initialize theme/accent colors from shared UI theme (mirrors Qt)
_saved_accent_color = config.get("accent_color")
if _saved_accent_color:
	set_accent_color(_saved_accent_color)
_theme_colors = get_colors()

# Page configuration
st.set_page_config(
	page_title="OnTheSpot - Streamlit UI",
	page_icon="🎵",
	layout="wide",
	initial_sidebar_state="expanded"
)

# Custom CSS for better styling (dark Spotify-inspired theme)
st.markdown(
	f"""
	<style>
		.stApp {{
			background-color: {_theme_colors['background']};
			color: {_theme_colors['text_primary']};
		}}
		.main-header {{
			font-size: 2.5rem;
			font-weight: bold;
			color: {_theme_colors['accent']};
			text-align: center;
			margin-bottom: 2rem;
		}}
		.stButton>button {{
			width: 100%;
			background-color: {_theme_colors['accent']};
			color: #000000;
		}}
		.stButton>button:hover {{
			background-color: {_theme_colors['accent_hover']};
		}}
		.download-stats {{
			background-color: {_theme_colors['background_elevated']};
			padding: 1rem;
			border-radius: 0.5rem;
			margin-bottom: 1rem;
		}}
		.status-bar {{
			background-color: {_theme_colors['background_elevated']};
			padding: 0.75rem 1rem;
			border-radius: 0.5rem;
			margin-bottom: 1rem;
			display: flex;
			justify-content: space-between;
			gap: 1rem;
			font-size: 0.9rem;
		}}
		.status-bar span {{
			white-space: nowrap;
			color: {_theme_colors['text_secondary']};
		}}
	</style>
	""",
	unsafe_allow_html=True,
)

# Initialize background workers (cached) and account loading helpers
@st.cache_resource
def initialize_workers():
    """Start all background workers once per backend process."""
    logger.info("Initializing OnTheSpot workers...")

    # Start parsing worker
    parsing_thread = threading.Thread(target=parsingworker, daemon=True)
    parsing_thread.start()

    # Start queue workers
    try:
        from .web import QueueWorker
    except ImportError:
        from onthespot.web import QueueWorker

    for _ in range(config.get('maximum_queue_workers', 2)):
        queue_worker = QueueWorker()
        queue_worker.daemon = True
        queue_worker.start()

    # Start download workers
    for _ in range(config.get('maximum_download_workers', 4)):
        download_worker = DownloadWorker()
        download_worker.daemon = True
        download_worker.start()

    # Start retry worker if enabled
    if config.get('enable_retry_worker', False):
        retry_worker = RetryWorker()
        retry_worker.daemon = True
        retry_worker.start()

    logger.info("All workers initialized successfully")
    return True


def reload_accounts_from_config() -> None:
    """Reload the global account_pool from the current config accounts.

    This mirrors the Qt FillAccountPool behaviour but can be called on demand
    from the Streamlit UI (e.g. after adding or removing accounts).
    """

    logger.info("Reloading account pool from config...")

    # Clear existing runtime accounts in-place
    try:
        while account_pool:
            account_pool.pop()
    except Exception as exc:
        logger.warning(f"Failed to clear account_pool cleanly: {exc}")

    # Refill from config
    fill_account_pool = FillAccountPool()
    fill_account_pool.start()
    fill_account_pool.wait()

    # Normalise active_account_number so it always points into account_pool
    active_idx = config.get("active_account_number", 0)
    if not account_pool:
        if active_idx != 0:
            config.set("active_account_number", 0)
            config.save()
    else:
        if active_idx < 0 or active_idx >= len(account_pool):
            config.set("active_account_number", 0)
            config.save()

    logger.info("Account pool reload complete: %d active account(s).", len(account_pool))


def render_status_bar() -> None:
    """Render a global status bar similar to the Qt status bar.

    Mirrors qt/mainui.py:update_status_bar for stealth and queue statistics.
    """

    # Stealth stats
    if config.get("stealth_mode_enabled"):
        try:
            stats = get_stealth_stats()
            max_hr = config.get("stealth_max_tracks_per_hour", 20)
            max_day = config.get("stealth_max_tracks_per_day", 100)
            stealth_text = (
                f"🛡️ Stealth: {stats.get('tracks_this_hour', 0)}/{max_hr} hr, "
                f"{stats.get('tracks_today', 0)}/{max_day} day"
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug(f"Failed to fetch stealth stats for status bar: {exc}")
            stealth_text = "🛡️ Stealth: N/A"
    else:
        stealth_text = "🛡️ Stealth: OFF"

    # Queue stats (mirror Qt logic)
    downloading = completed = waiting = failed = stealth_waiting = 0
    try:
        with download_queue_lock:
            for item in download_queue.values():
                status = str(item.get("item_status", "")).lower()
                if status in ("downloading", "converting", "getting info"):
                    downloading += 1
                elif status in ("downloaded", "already exists") or "done" in status:
                    completed += 1
                elif status == "waiting":
                    waiting += 1
                elif "wait" in status:
                    # Stealth waiting (e.g. "Done · Wait 1m 30s")
                    stealth_waiting += 1
                elif status == "failed" or "fail" in status:
                    failed += 1
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug(f"Failed to compute queue stats for status bar: {exc}")

    queue_text = f"📥 {downloading} active, {completed} done"
    if waiting > 0:
        queue_text += f", {waiting} queued"
    if stealth_waiting > 0:
        queue_text += f", {stealth_waiting} stealth"
    if failed > 0:
        queue_text += f", {failed} failed"

    # Overall queue depths across stages (parsing/pending/download)
    try:
        sizes = get_queue_sizes()
        pipeline_text = (
            f"🔁 Queues: parsing {sizes.get('parsing', 0)}, "
            f"pending {sizes.get('pending', 0)}, "
            f"download {sizes.get('download_queue', 0)}"
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug(f"Failed to compute queue sizes for status bar: {exc}")
        pipeline_text = "🔁 Queues: N/A"

    # Speed indicator
    if downloading > 0:
        speed_text = f"⬇️ {downloading} downloading..."
    else:
        speed_text = "⬇️ Idle"

    st.markdown(
        f'<div class="status-bar">'
        f"<span>{stealth_text}</span>"
        f"<span>{queue_text}</span>"
        f"<span>{pipeline_text}</span>"
        f"<span>{speed_text}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


def notify(message: str, level: str = "info", download: bool = False) -> None:
    """Display a notification, mirroring Qt's show_popup_dialog semantics.

    When download is True and disable_download_popups is enabled, the message
    is suppressed (Qt uses this only for per-item download popups).
    """

    if download and config.get("disable_download_popups", False):
        return

    if level == "success":
        st.success(message)
    elif level == "warning":
        st.warning(message)
    elif level == "error":
        st.error(message)
    else:
        st.info(message)


def get_active_service():
    """Return the service code for the currently active account, or None."""

    if not account_pool:
        return None

    idx = config.get("active_account_number", 0)
    if idx < 0 or idx >= len(account_pool):
        idx = 0

    try:
        return account_pool[idx].get("service")
    except Exception:  # pragma: no cover - defensive
        return None


def render_search_page() -> None:
    """Render the 🔍 Search page."""

    st.header("🔍 Search Music")

    # Initialize session state for search results so they persist across reruns
    if "search_results" not in st.session_state:
        st.session_state["search_results"] = []

    # Search input
    search_query = st.text_input(
        "Enter search term or URL",
        placeholder=(
            "Search for tracks, albums, artists, playlists, podcasts, episodes, "
            "audiobooks, or paste a URL..."
        ),
    )

    # Content type filters (mirror PyQt search types)
    st.markdown("**Search for:**")

    # Simple vertical list to keep things tidy and aligned
    search_tracks = st.checkbox(
        "Tracks", value=config.get("enable_search_tracks", True)
    )
    search_albums = st.checkbox(
        "Albums", value=config.get("enable_search_albums", True)
    )
    search_playlists = st.checkbox(
        "Playlist", value=config.get("enable_search_playlists", True)
    )
    search_artists = st.checkbox(
        "Artists", value=config.get("enable_search_artists", True)
    )
    search_podcasts = st.checkbox(
        "Podcasts", value=config.get("enable_search_podcasts", False)
    )
    search_episodes = st.checkbox(
        "Episodes", value=config.get("enable_search_episodes", False)
    )
    search_audiobooks = st.checkbox(
        "Audiobooks", value=config.get("enable_search_audiobooks", False)
    )

    # Search button
    if st.button("🔍 Search", type="primary"):
        if not search_query:
            notify("Please enter a search term or URL.", level="warning")
        else:
            content_types = []
            if search_tracks:
                content_types.append("track")
            if search_albums:
                content_types.append("album")
            if search_playlists:
                content_types.append("playlist")
            if search_artists:
                content_types.append("artist")
            if search_podcasts:
                content_types.append("show")
            if search_episodes:
                content_types.append("episode")
            if search_audiobooks:
                content_types.append("audiobook")

            if not content_types:
                notify(
                    "Please select at least one content type to search (Tracks, Albums, "
                    "Artists, Playlist, Podcasts, Episodes, Audiobooks).",
                    level="warning",
                )
            else:
                # Persist search filter choices as defaults, so Settings → Search reflects them
                config.set("enable_search_tracks", search_tracks)
                config.set("enable_search_albums", search_albums)
                config.set("enable_search_playlists", search_playlists)
                config.set("enable_search_artists", search_artists)
                config.set("enable_search_podcasts", search_podcasts)
                config.set("enable_search_episodes", search_episodes)
                config.set("enable_search_audiobooks", search_audiobooks)
                config.save()

                with st.spinner("Searching..."):
                    results = get_search_results(
                        search_query, content_types=content_types
                    )

                    # Interpret results similar to Qt's search logic
                    if results is None:
                        st.session_state["search_results"] = []
                        notify(
                            "You need to login to at least one account to use this feature.",
                            level="error",
                        )
                    elif results is True:
                        # Direct URL(s) or file path passed straight to the parser
                        st.session_state["search_results"] = []
                        url_inputs = [
                            url.strip()
                            for url in search_query.splitlines()
                            if url.strip()
                        ]
                        if len(url_inputs) > 1:
                            notify(
                                "Items are being parsed and will be added to the download queue shortly."
                            )
                        else:
                            notify(
                                "Item is being parsed and will be added to the download queue shortly."
                            )
                    elif results is False:
                        st.session_state["search_results"] = []
                        active_service = get_active_service()
                        if active_service == "generic":
                            notify(
                                "Generic Downloader does not support search, please enter a supported URL.",
                                level="error",
                            )
                        else:
                            notify(
                                "Invalid item, please check your query or account settings.",
                                level="error",
                            )
                    elif isinstance(results, list) and len(results) > 0:
                        st.session_state["search_results"] = results
                        notify(f"Found {len(results)} results.", level="success")
                    else:
                        st.session_state["search_results"] = []
                        notify("No results found.", level="info")

    # Always render stored search results so Download buttons work on every rerun
    results = st.session_state.get("search_results", [])
    if isinstance(results, list) and len(results) > 0:
        # Display results in a table
        for idx, item in enumerate(results):
            with st.container():
                col1, col2, col3 = st.columns([1, 4, 1])

                with col1:
                    if item.get("item_thumbnail_url"):
                        st.image(item["item_thumbnail_url"], width=80)

                with col2:
                    st.markdown(f"**{item.get('item_name', 'Unknown')}**")
                    st.caption(
                        f"{item.get('item_by', 'Unknown Artist')} • "
                        f"{item.get('item_type', 'track').title()}"
                    )
                    st.caption(
                        f"Service: {item.get('item_service', 'unknown').replace('_', ' ').title()}"
                    )

                with col3:
                    if st.button("⬇️ Download", key=f"download_{idx}"):
                        parse_url(item["item_url"])
                        item_type = item.get("item_type", "item").title()
                        item_name = item.get("item_name", "Unknown")
                        notify(
                            f"{item_type}: {item_name} is being parsed and will be "
                            f"added to the download queue shortly.",
                            level="info",
                            download=True,
                        )

            st.divider()


def render_download_queue_page() -> None:
    """Render the 📥 Download Queue page."""

    st.header("📥 Download Queue")

    # Queue statistics
    with download_queue_lock:
        queue_items = list(download_queue.values())

    total_items = len(queue_items)
    downloading = sum(
        1 for item in queue_items if item.get("item_status") == "Downloading"
    )
    waiting = sum(1 for item in queue_items if item.get("item_status") == "Waiting")
    completed = sum(
        1 for item in queue_items if item.get("item_status") == "Downloaded"
    )
    failed = sum(
        1
        for item in queue_items
        if item.get("item_status") in ("Failed", "Cancelled", "Unavailable")
    )

    # Display stats
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total", total_items)
    col2.metric("Downloading", downloading)
    col3.metric("Waiting", waiting)
    col4.metric("Completed", completed)
    col5.metric("Failed", failed)

    st.divider()

    # Queue actions
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Retry Failed", use_container_width=True):
            with download_queue_lock:
                for local_id, item in download_queue.items():
                    if item["item_status"] in ("Failed", "Cancelled"):
                        download_queue[local_id]["item_status"] = "Waiting"
            st.success("Retrying failed items...")
            time.sleep(0.5)
            st.rerun()

    with col2:
        if st.button("🗑️ Clear Completed", use_container_width=True):
            with download_queue_lock:
                keys_to_delete = [
                    local_id
                    for local_id, item in download_queue.items()
                    if item["item_status"]
                    in (
                        "Downloaded",
                        "Already Exists",
                        "Cancelled",
                        "Unavailable",
                        "Deleted",
                    )
                ]
                for key in keys_to_delete:
                    del download_queue[key]
            st.success("Cleared completed items...")
            time.sleep(0.5)
            st.rerun()

    with col3:
        if st.button("❌ Cancel All", use_container_width=True):
            with pending_lock:
                pending.clear()
            with download_queue_lock:
                for local_id, item in download_queue.items():
                    if item["item_status"] == "Waiting":
                        download_queue[local_id]["item_status"] = "Cancelled"
            st.warning("Cancelled all waiting items...")
            time.sleep(0.5)
            st.rerun()

    st.divider()

    # Download queue filter settings (mirror Qt download queue filters)
    (
        filter_col1,
        filter_col2,
        filter_col3,
        filter_col4,
        filter_col5,
    ) = st.columns(5)
    cfg_show_waiting = config.get("download_queue_show_waiting", True)
    cfg_show_failed = config.get("download_queue_show_failed", True)
    cfg_show_unavailable = config.get("download_queue_show_unavailable", True)
    cfg_show_cancelled = config.get("download_queue_show_cancelled", True)
    cfg_show_completed = config.get("download_queue_show_completed", True)

    with filter_col1:
        show_waiting = st.checkbox(
            "Waiting", value=cfg_show_waiting, key="queue_filter_waiting"
        )
    with filter_col2:
        show_failed = st.checkbox(
            "Failed", value=cfg_show_failed, key="queue_filter_failed"
        )
    with filter_col3:
        show_unavailable = st.checkbox(
            "Unavailable",
            value=cfg_show_unavailable,
            key="queue_filter_unavailable",
        )
    with filter_col4:
        show_cancelled = st.checkbox(
            "Cancelled",
            value=cfg_show_cancelled,
            key="queue_filter_cancelled",
        )
    with filter_col5:
        show_completed = st.checkbox(
            "Completed",
            value=cfg_show_completed,
            key="queue_filter_completed",
        )

    # Persist filter preferences back to config when they change
    if show_waiting != cfg_show_waiting:
        config.set("download_queue_show_waiting", show_waiting)
        config.save()
    if show_failed != cfg_show_failed:
        config.set("download_queue_show_failed", show_failed)
        config.save()
    if show_unavailable != cfg_show_unavailable:
        config.set("download_queue_show_unavailable", show_unavailable)
        config.save()
    if show_cancelled != cfg_show_cancelled:
        config.set("download_queue_show_cancelled", show_cancelled)
        config.save()
    if show_completed != cfg_show_completed:
        config.set("download_queue_show_completed", show_completed)
        config.save()

    # Apply filters when displaying queue items
    def _queue_item_visible(status: str) -> bool:
        if status == "Waiting" and not show_waiting:
            return False
        if status == "Failed" and not show_failed:
            return False
        if status == "Unavailable" and not show_unavailable:
            return False
        if status == "Cancelled" and not show_cancelled:
            return False
        if status in ("Already Exists", "Downloaded") and not show_completed:
            return False
        return True

    # Display queue items
    if total_items > 0:
        for item in queue_items:
            status = item.get("item_status", "Unknown")
            if not _queue_item_visible(status):
                continue

            with st.container():
                col1, col2, col3, col4 = st.columns([1, 4, 2, 1])

                with col1:
                    if item.get("item_thumbnail"):
                        st.image(item["item_thumbnail"], width=60)

                with col2:
                    st.markdown(f"**{item.get('item_name', 'Unknown')}**")
                    st.caption(f"{item.get('item_by', 'Unknown Artist')}")
                    st.caption(
                        f"Service: {item.get('item_service', 'unknown').replace('_', ' ').title()}"
                    )

                with col3:
                    if status == "Downloading":
                        progress = item.get("progress", 0)
                        st.progress(progress / 100 if progress > 0 else 0)
                        st.caption(f"Downloading: {progress}%")
                    elif status == "Downloaded":
                        st.success("✅ Downloaded")
                    elif status == "Waiting":
                        st.info("⏳ Waiting")
                    elif status in ("Failed", "Cancelled", "Unavailable"):
                        st.error(f"❌ {status}")
                    else:
                        st.caption(status)

                with col4:
                    file_path = item.get("file_path")

                    # Cancel / retry actions
                    if status == "Waiting":
                        if st.button(
                            "❌", key=f"cancel_{item['local_id']}", help="Cancel"
                        ):
                            download_queue[item["local_id"]]["item_status"] = "Cancelled"
                            st.rerun()
                    elif status in ("Failed", "Cancelled"):
                        if st.button(
                            "🔄", key=f"retry_{item['local_id']}", help="Retry"
                        ):
                            download_queue[item["local_id"]]["item_status"] = "Waiting"
                            st.rerun()

                    # Open file / containing folder once download is available
                    if status in ("Downloaded", "Already Exists") and file_path:
                        if config.get("download_open_btn", True):
                            if st.button(
                                "📄",
                                key=f"open_{item['local_id']}",
                                help="Open file",
                            ):
                                try:
                                    open_item(os.path.abspath(file_path))
                                except Exception as e:
                                    st.error(f"Could not open file: {e}")
                        if config.get("download_locate_btn", True):
                            if st.button(
                                "📁",
                                key=f"folder_{item['local_id']}",
                                help="Open containing folder",
                            ):
                                try:
                                    open_item(os.path.dirname(os.path.abspath(file_path)))
                                except Exception as e:
                                    st.error(f"Could not open folder: {e}")

                    # Delete downloaded file (mirrors Qt delete button)
                    if config.get("download_delete_btn", False) and file_path:
                        if st.button(
                            "🗑️",
                            key=f"delete_{item['local_id']}",
                            help="Delete file",
                        ):
                            try:
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                                download_queue[item["local_id"]]["item_status"] = "Deleted"
                                download_queue[item["local_id"]]["file_path"] = None
                            except Exception as e:
                                st.error(f"Could not delete file: {e}")
                            else:
                                st.success("File deleted")
                            st.rerun()

                st.divider()
    else:
        st.info("Download queue is empty")

    # Auto-refresh
    if st.session_state.auto_refresh and (downloading > 0 or waiting > 0):
        time.sleep(st.session_state.refresh_interval)
        st.rerun()


def render_settings_page() -> None:
    """Render the ⚙️ Settings page (mirrors Qt Settings dialog)."""

    st.header("⚙️ Settings")

    # Settings are organized to mirror the PyQt Settings dialog structure
    (
        accounts_tab,
        general_tab,
        search_tab,
        queue_tab,
        audio_tab,
        metadata_tab,
        video_tab,
    ) = st.tabs(
        [
            "Accounts",
            "General",
            "Search",
            "Download Queue",
            "Audio Downloads",
            "Audio Metadata",
            "Video Downloads",
        ]
    )

    # --- Accounts Tab ---
    with accounts_tab:
        st.subheader("Accounts")

        # Read configured accounts from config and overlay runtime status from account_pool
        try:
            accounts_cfg = config.get("accounts", []).copy()
        except Exception:
            accounts_cfg = []

        if not accounts_cfg:
            st.info("No accounts configured in config.")
        else:
            account_rows = []
            for acc in accounts_cfg:
                uuid = acc.get("uuid", "-")
                service = acc.get("service", "-")
                active_cfg = acc.get("active", True)

                runtime = next(
                    (a for a in account_pool if a.get("uuid") == uuid), None
                )

                if runtime is not None:
                    username = (
                        runtime.get("username")
                        or acc.get("login", {}).get("username")
                        or "-"
                    )
                    account_type = str(
                        runtime.get("account_type", acc.get("account_type", "-"))
                    ).title()
                    bitrate = runtime.get("bitrate", acc.get("bitrate", "-"))
                    status = str(runtime.get("status", "active")).title()
                else:
                    username = (
                        acc.get("login", {}).get("username")
                        or acc.get("username")
                        or "-"
                    )
                    account_type = str(acc.get("account_type", "-")).title()
                    bitrate = acc.get("bitrate", "-")
                    status = "Not Loaded"

                account_rows.append(
                    {
                        "UUID": uuid,
                        "Username": username,
                        "Service": service.replace("_", " ").title(),
                        "Active (config)": "Yes" if active_cfg else "No",
                        "Bitrate": bitrate,
                        "Status": status,
                    }
                )

            if account_rows:
                df_accounts = pd.DataFrame(account_rows)
                st.dataframe(df_accounts, use_container_width=True, hide_index=True)

        # Active account selection (mirrors Qt radio buttons, uses runtime pool)
        if len(account_pool) > 0:
            current_active = config.get("active_account_number", 0)
            if current_active < 0 or current_active >= len(account_pool):
                current_active = 0

            def _format_account_option(i: int) -> str:
                acc = account_pool[i]
                username = acc.get("username", "Unknown")
                service = acc.get("service", "-").replace("_", " ").title()
                return f"{i}: {username} ({service})"

            selected_active = st.radio(
                "Active account",
                options=list(range(len(account_pool))),
                index=current_active,
                format_func=_format_account_option,
                key="accounts_active_radio",
            )

            if selected_active != current_active:
                config.set("active_account_number", selected_active)
                config.save()
                st.success("Active account updated.")
        else:
            st.info("No active accounts in runtime pool (logins may have failed).")

        # Remove accounts from config and reload runtime pool
        if accounts_cfg:
            st.markdown("---")
            st.subheader("Remove accounts")

            for idx, acc in enumerate(accounts_cfg):
                uuid = acc.get("uuid", "-")
                runtime = next(
                    (a for a in account_pool if a.get("uuid") == uuid), None
                )

                if runtime is not None:
                    username = runtime.get("username", "Unknown")
                    service_name = runtime.get("service", "-").replace(
                        "_", " "
                    ).title()
                    status_text = str(runtime.get("status", "unknown")).title()
                else:
                    username = (
                        acc.get("login", {}).get("username")
                        or acc.get("username")
                        or "Unknown"
                    )
                    service_name = acc.get("service", "-").replace("_", " ").title()
                    status_text = "Not Loaded"

                col_a, col_b, col_c = st.columns([4, 4, 2])
                with col_a:
                    st.write(f"{idx}: {username} ({service_name})")
                with col_b:
                    st.write(status_text)
                with col_c:
                    if st.button("Remove", key=f"remove_account_{idx}"):
                        new_cfg = [a for j, a in enumerate(accounts_cfg) if j != idx]
                        config.set("accounts", new_cfg)
                        config.save()
                        reload_accounts_from_config()
                        st.success("Account removed.")
                        st.rerun()

        st.markdown("---")
        st.subheader("Add new account")

        service_options = [
            "Spotify",
            "YouTube Music",
            "Apple Music",
            "SoundCloud",
            "Bandcamp",
            "Deezer",
            "Qobuz",
            "Tidal",
            "Crunchyroll",
            "Generic Downloader",
        ]
        service_choice = st.selectbox(
            "Service",
            options=service_options,
            key="accounts_add_service",
        )

        if st.button("Add account", key="btn_add_account"):
            try:
                service_map = {
                    "Spotify": spotify_new_session,
                    "YouTube Music": youtube_music_add_account,
                    "Apple Music": apple_music_add_account,
                    "SoundCloud": soundcloud_add_account,
                    "Bandcamp": bandcamp_add_account,
                    "Deezer": deezer_add_account,
                    "Qobuz": qobuz_add_account,
                    "Tidal": tidal_add_account_pt1,
                    "Crunchyroll": crunchyroll_add_account,
                }

                if service_choice == "Generic Downloader":
                    generic_add_account()
                else:
                    add_fn = service_map.get(service_choice)
                    if add_fn is None:
                        raise RuntimeError(f"Unsupported service: {service_choice}")
                    add_fn()

                reload_accounts_from_config()
                st.success(f"Account added for {service_choice}.")
                st.rerun()
            except Exception as exc:
                st.error(f"Failed to add account: {exc}")

        # Generic extractor info / helper
        service_code = get_active_service()
        if service_code == "generic":
            try:
                extractors = generic_list_extractors()
            except Exception as e:  # pragma: no cover - defensive
                extractors = []
                logger.error(f"Failed to list generic extractors: {e}")
            if extractors:
                st.markdown(
                    "The following services are officially supported by the generic downloader:"\
                    "<br>" + "<br>".join(extractors),
                    unsafe_allow_html=True,
                )
            if st.button("Add Generic downloader", key="btn_add_generic"):
                try:
                    generic_add_account()
                    reload_accounts_from_config()
                    st.success("Generic downloader added and loaded.")
                    st.rerun()
                except Exception as e:  # pragma: no cover - defensive
                    st.error(f"Failed to add Generic downloader: {e}")

        st.markdown("---")
        if st.button("Reload accounts from config", key="btn_reload_accounts"):
            reload_accounts_from_config()
            st.success("Accounts reloaded from config.")
            st.rerun()

    # --- General Tab ---
    with general_tab:
        st.subheader("General settings")

        # Language
        language_options = ["English", "Deutsch", "Português"]
        current_language = config.get("language", "English")
        try:
            lang_index = language_options.index(current_language)
        except ValueError:
            lang_index = 0

        language = st.selectbox(
            "Language",
            language_options,
            index=lang_index,
            key="general_language",
        )
        explicit_label = st.text_input(
            "Explicit label",
            value=config.get("explicit_label", "Explicit"),
            key="general_explicit_label",
        )

        # Appearance / theme (shared accent color with Qt)
        current_accent = config.get("accent_color", get_accent_color())
        accent_color = st.color_picker(
            "Accent color",
            value=current_accent,
            key="general_accent_color",
            help="Primary accent color used across all UIs (Qt and Streamlit)",
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            download_copy_btn = st.checkbox(
                "Show Copy button",
                value=config.get("download_copy_btn", True),
                key="general_download_copy_btn",
            )
            download_open_btn = st.checkbox(
                "Show Open button",
                value=config.get("download_open_btn", True),
                key="general_download_open_btn",
            )
        with col2:
            download_locate_btn = st.checkbox(
                "Show Locate button",
                value=config.get("download_locate_btn", True),
                key="general_download_locate_btn",
            )
            download_delete_btn = st.checkbox(
                "Show Delete button",
                value=config.get("download_delete_btn", False),
                key="general_download_delete_btn",
            )
        with col3:
            show_search_thumbnails = st.checkbox(
                "Show search thumbnails",
                value=config.get("show_search_thumbnails", True),
                key="general_show_search_thumbnails",
            )
            show_download_thumbnails = st.checkbox(
                "Show download thumbnails",
                value=config.get("show_download_thumbnails", True),
                key="general_show_download_thumbnails",
            )

        col4, col5, col6 = st.columns(3)
        with col4:
            thumbnail_size = st.number_input(
                "Thumbnail size",
                min_value=32,
                max_value=512,
                value=config.get("thumbnail_size", 128),
                step=1,
                key="general_thumbnail_size",
            )
        with col5:
            max_search_results = st.number_input(
                "Max search results",
                min_value=1,
                max_value=1000,
                value=config.get("max_search_results", 50),
                step=1,
                key="general_max_search_results",
            )
        with col6:
            disable_download_popups = st.checkbox(
                "Disable download popups",
                value=config.get("disable_download_popups", False),
                key="general_disable_download_popups",
            )

        col7, col8, col9 = st.columns(3)
        with col7:
            windows_10_explorer_thumbnails = st.checkbox(
                "Windows Explorer thumbnails",
                value=config.get("windows_10_explorer_thumbnails", False),
                key="general_win_thumb",
            )
            mirror_spotify_playback = st.checkbox(
                "Mirror Spotify playback",
                value=config.get("mirror_spotify_playback", False),
                key="general_mirror_spotify",
            )
        with col8:
            stealth_mode_enabled = st.checkbox(
                "Enable Stealth mode",
                value=config.get("stealth_mode_enabled", False),
                key="general_stealth_mode",
            )
            close_to_tray = st.checkbox(
                "Close to tray",
                value=config.get("close_to_tray", False),
                key="general_close_to_tray",
            )
        with col9:
            check_for_updates = st.checkbox(
                "Check for updates",
                value=config.get("check_for_updates", True),
                key="general_check_for_updates",
            )
            raw_media_download = st.checkbox(
                "Raw media download",
                value=config.get("raw_media_download", False),
                key="general_raw_media_download",
            )

        col10, col11 = st.columns(2)
        with col10:
            illegal_character_replacement = st.text_input(
                "Illegal character replacement",
                value=config.get("illegal_character_replacement", "_"),
                key="general_illegal_characters",
            )
        with col11:
            rotate_active_account_number = st.checkbox(
                "Rotate active account for metadata",
                value=config.get("rotate_active_account_number", False),
                key="general_rotate_active",
            )

        st.markdown("---")
        st.subheader("Workers & performance")

        colw1, colw2, colw3 = st.columns(3)
        with colw1:
            download_delay = st.number_input(
                "Download delay (ms)",
                min_value=0,
                max_value=10000,
                value=config.get("download_delay", 0),
                step=50,
                key="general_download_delay",
            )
        with colw2:
            # Chunk size is stored and used as bytes in the backend (downloader.py / Qt settings)
            # Use bytes here too, with a wide safe range, to avoid Streamlit max_value errors.
            _raw_chunk = int(config.get("download_chunk_size", 65536))
            _raw_chunk = max(1024, min(1048576, _raw_chunk))
            download_chunk_size = st.number_input(
                "Download chunk size (bytes)",
                min_value=1024,
                max_value=1_048_576,
                value=_raw_chunk,
                step=1024,
                key="general_download_chunk",
            )
        with colw3:
            maximum_queue_workers = st.number_input(
                "Max queue workers",
                min_value=1,
                max_value=16,
                value=config.get("maximum_queue_workers", 2),
                step=1,
                key="general_queue_workers",
            )

        colw4, colw5 = st.columns(2)
        with colw4:
            maximum_download_workers = st.number_input(
                "Max download workers",
                min_value=1,
                max_value=16,
                value=config.get("maximum_download_workers", 4),
                step=1,
                key="general_download_workers",
            )
        with colw5:
            enable_retry_worker = st.checkbox(
                "Enable retry worker",
                value=config.get("enable_retry_worker", False),
                key="general_retry_worker",
            )
            retry_worker_delay = st.number_input(
                "Retry worker delay (s)",
                min_value=1,
                max_value=3600,
                value=config.get("retry_worker_delay", 30),
                step=1,
                key="general_retry_delay",
            )

        st.markdown("---")
        st.subheader("Maintenance")
        tool_col1, tool_col2 = st.columns(2)
        with tool_col1:
            confirm_clear = st.checkbox(
                "I understand this will delete cached requests and logs",
                key="confirm_clear_cache",
            )
            if st.button("Clear cache"):
                if not confirm_clear:
                    notify(
                        "Please confirm you want to clear the cache by ticking the box above.",
                        level="warning",
                    )
                else:
                    reqcache_path = os.path.join(cache_dir(), "reqcache")
                    logs_path = os.path.join(cache_dir(), "logs")
                    try:
                        shutil.rmtree(reqcache_path, ignore_errors=True)
                        shutil.rmtree(logs_path, ignore_errors=True)
                        notify(
                            f"Cache cleared.\n\nDeleted:\n- {reqcache_path}\n- {logs_path}",
                            level="success",
                        )
                    except Exception as e:  # pragma: no cover - defensive
                        notify(f"Failed to clear cache: {e}", level="error")
        with tool_col2:
            if st.button("Export logs to Downloads"):
                logs_src = os.path.join(
                    cache_dir(),
                    "logs",
                    getattr(config, "session_uuid", ""),
                    "onthespot.log",
                )
                dst_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                dst_path = os.path.join(dst_dir, "onthespot.log")
                try:
                    if not os.path.isfile(logs_src):
                        notify(
                            f"No log file found for this session at: {logs_src}",
                            level="error",
                        )
                    else:
                        os.makedirs(dst_dir, exist_ok=True)
                        shutil.copy(logs_src, dst_path)
                        notify(
                            f"Logs exported to '{dst_path}'",
                            level="success",
                        )
                except Exception as e:  # pragma: no cover - defensive
                    notify(f"Failed to export logs: {e}", level="error")

    # --- Search Tab ---
    with search_tab:
        st.subheader("Search")

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            enable_search_tracks = st.checkbox(
                "Tracks",
                value=config.get("enable_search_tracks"),
                key="search_tracks",
            )
            enable_search_albums = st.checkbox(
                "Albums",
                value=config.get("enable_search_albums"),
                key="search_albums",
            )
            enable_search_playlists = st.checkbox(
                "Playlist",
                value=config.get("enable_search_playlists"),
                key="search_playlists",
            )
        with col_s2:
            enable_search_artists = st.checkbox(
                "Artists",
                value=config.get("enable_search_artists"),
                key="search_artists",
            )
            enable_search_episodes = st.checkbox(
                "Episodes",
                value=config.get("enable_search_episodes"),
                key="search_episodes",
            )
            enable_search_podcasts = st.checkbox(
                "Podcasts",
                value=config.get("enable_search_podcasts"),
                key="search_podcasts",
            )
            enable_search_audiobooks = st.checkbox(
                "Audiobooks",
                value=config.get("enable_search_audiobooks"),
                key="search_audiobooks",
            )

    # --- Download Queue Tab ---
    with queue_tab:
        st.subheader("Download queue filters")

        col_q1, col_q2, col_q3, col_q4, col_q5 = st.columns(5)
        with col_q1:
            dq_show_waiting = st.checkbox(
                "Waiting",
                value=config.get("download_queue_show_waiting", True),
                key="dq_show_waiting",
            )
        with col_q2:
            dq_show_failed = st.checkbox(
                "Failed",
                value=config.get("download_queue_show_failed", True),
                key="dq_show_failed",
            )
        with col_q3:
            dq_show_unavailable = st.checkbox(
                "Unavailable",
                value=config.get("download_queue_show_unavailable", True),
                key="dq_show_unavailable",
            )
        with col_q4:
            dq_show_cancelled = st.checkbox(
                "Cancelled",
                value=config.get("download_queue_show_cancelled", True),
                key="dq_show_cancelled",
            )
        with col_q5:
            dq_show_completed = st.checkbox(
                "Completed",
                value=config.get("download_queue_show_completed", True),
                key="dq_show_completed",
            )

    # --- Audio Downloads Tab ---
    with audio_tab:
        st.subheader("Audio download settings")

        audio_download_path = st.text_input(
            "Audio download path",
            value=config.get("audio_download_path", ""),
            key="audio_download_path",
        )

        col_a1, col_a2 = st.columns(2)
        with col_a1:
            track_file_format = st.text_input(
                "Track file format",
                value=config.get("track_file_format", "{track_name}"),
                key="track_file_format",
            )
            track_path_formatter = st.text_input(
                "Track path formatter",
                value=config.get("track_path_formatter", "{artist}/{album}"),
                key="track_path_formatter",
            )
            podcast_file_format = st.text_input(
                "Podcast file format",
                value=config.get("podcast_file_format", "{episode_name}"),
                key="podcast_file_format",
            )
            podcast_path_formatter = st.text_input(
                "Podcast path formatter",
                value=config.get("podcast_path_formatter", "{show_name}"),
                key="podcast_path_formatter",
            )
        with col_a2:
            use_playlist_path = st.checkbox(
                "Use playlist path for playlist items",
                value=config.get("use_playlist_path", False),
                key="use_playlist_path",
            )
            playlist_path_formatter = st.text_input(
                "Playlist path formatter",
                value=config.get("playlist_path_formatter", "{playlist_name}"),
                key="playlist_path_formatter",
            )
            create_m3u_file = st.checkbox(
                "Create M3U file",
                value=config.get("create_m3u_file", False),
                key="create_m3u_file",
            )
            m3u_path_formatter = st.text_input(
                "M3U path formatter",
                value=config.get("m3u_path_formatter", "{playlist_name}.m3u"),
                key="m3u_path_formatter",
            )

        col_a3, col_a4 = st.columns(2)
        with col_a3:
            extinf_separator = st.text_input(
                "EXTINF separator",
                value=config.get("extinf_separator", " - "),
                key="extinf_separator",
            )
            extinf_label = st.text_input(
                "EXTINF label",
                value=config.get("extinf_label", "#EXTINF"),
                key="extinf_label",
            )
            save_album_cover = st.checkbox(
                "Save album cover",
                value=config.get("save_album_cover", True),
                key="save_album_cover",
            )
        with col_a4:
            album_cover_format = st.text_input(
                "Album cover format",
                value=config.get("album_cover_format", "jpg"),
                key="album_cover_format",
            )
            file_bitrate = st.text_input(
                "File bitrate (kbps)",
                value=config.get("file_bitrate", "320"),
                key="file_bitrate",
            )
            file_hertz = st.number_input(
                "Sample rate (Hz)",
                min_value=8000,
                max_value=192000,
                value=config.get("file_hertz", 44100),
                step=1000,
                key="file_hertz",
            )

        col_a5, col_a6 = st.columns(2)
        with col_a5:
            use_custom_file_bitrate = st.checkbox(
                "Use custom file bitrate",
                value=config.get("use_custom_file_bitrate", False),
                key="use_custom_file_bitrate",
            )
            download_lyrics = st.checkbox(
                "Download lyrics",
                value=config.get("download_lyrics", False),
                key="download_lyrics",
            )
        with col_a6:
            only_download_synced_lyrics = st.checkbox(
                "Only synced lyrics",
                value=config.get("only_download_synced_lyrics", False),
                key="only_synced_lyrics",
            )
            only_download_plain_lyrics = st.checkbox(
                "Only plain lyrics",
                value=config.get("only_download_plain_lyrics", False),
                key="only_plain_lyrics",
            )
            save_lrc_file = st.checkbox(
                "Save .lrc file",
                value=config.get("save_lrc_file", False),
                key="save_lrc_file",
            )

        translate_file_path = st.checkbox(
            "Translate file path to Latin characters",
            value=config.get("translate_file_path", False),
            key="translate_file_path",
        )

        st.markdown("---")
        st.subheader("Legacy download root & format (CLI compatibility)")
        col_legacy1, col_legacy2, col_legacy3 = st.columns(3)
        with col_legacy1:
            download_root = st.text_input(
                "Download root",
                value=config.get("download_root", ""),
                key="download_root",
            )
        with col_legacy2:
            media_format = st.selectbox(
                "Audio format",
                ["mp3", "ogg", "flac", "m4a"],
                index=["mp3", "ogg", "flac", "m4a"].index(
                    config.get("media_format", "mp3")
                ),
                key="media_format",
            )
        with col_legacy3:
            download_quality = st.selectbox(
                "Audio quality",
                ["low", "medium", "high", "very_high"],
                index=["low", "medium", "high", "very_high"].index(
                    config.get("download_quality", "high")
                ),
                key="download_quality",
            )

    # --- Audio Metadata Tab ---
    with metadata_tab:
        st.subheader("Audio metadata settings")

        metadata_separator = st.text_input(
            "Metadata separator",
            value=config.get("metadata_separator", " / "),
            key="metadata_separator",
        )
        overwrite_existing_metadata = st.checkbox(
            "Overwrite existing metadata",
            value=config.get("overwrite_existing_metadata", True),
            key="overwrite_metadata",
        )

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            embed_branding = st.checkbox(
                "Branding",
                value=config.get("embed_branding", True),
                key="embed_branding",
            )
            embed_cover = st.checkbox(
                "Cover",
                value=config.get("embed_cover", True),
                key="embed_cover",
            )
            embed_artist = st.checkbox(
                "Artist",
                value=config.get("embed_artist", True),
                key="embed_artist",
            )
            embed_album = st.checkbox(
                "Album",
                value=config.get("embed_album", True),
                key="embed_album",
            )
            embed_albumartist = st.checkbox(
                "Album artist",
                value=config.get("embed_albumartist", True),
                key="embed_albumartist",
            )
            embed_name = st.checkbox(
                "Track name",
                value=config.get("embed_name", True),
                key="embed_name",
            )
        with col_m2:
            embed_year = st.checkbox(
                "Year",
                value=config.get("embed_year", True),
                key="embed_year",
            )
            embed_discnumber = st.checkbox(
                "Disc number",
                value=config.get("embed_discnumber", True),
                key="embed_discnumber",
            )
            embed_tracknumber = st.checkbox(
                "Track number",
                value=config.get("embed_tracknumber", True),
                key="embed_tracknumber",
            )
            embed_genre = st.checkbox(
                "Genre",
                value=config.get("embed_genre", True),
                key="embed_genre",
            )
            embed_performers = st.checkbox(
                "Performers",
                value=config.get("embed_performers", False),
                key="embed_performers",
            )
            embed_producers = st.checkbox(
                "Producers",
                value=config.get("embed_producers", False),
                key="embed_producers",
            )
        with col_m3:
            embed_writers = st.checkbox(
                "Writers",
                value=config.get("embed_writers", False),
                key="embed_writers",
            )
            embed_label = st.checkbox(
                "Label",
                value=config.get("embed_label", False),
                key="embed_label",
            )
            embed_copyright = st.checkbox(
                "Copyright",
                value=config.get("embed_copyright", False),
                key="embed_copyright",
            )
            embed_description = st.checkbox(
                "Description",
                value=config.get("embed_description", False),
                key="embed_description",
            )
            embed_language = st.checkbox(
                "Language",
                value=config.get("embed_language", False),
                key="embed_language",
            )
            embed_isrc = st.checkbox(
                "ISRC",
                value=config.get("embed_isrc", False),
                key="embed_isrc",
            )
        with col_m4:
            embed_length = st.checkbox(
                "Length",
                value=config.get("embed_length", False),
                key="embed_length",
            )
            embed_url = st.checkbox(
                "URL",
                value=config.get("embed_url", False),
                key="embed_url",
            )
            embed_key = st.checkbox(
                "Key",
                value=config.get("embed_key", False),
                key="embed_key",
            )
            embed_bpm = st.checkbox(
                "BPM",
                value=config.get("embed_bpm", False),
                key="embed_bpm",
            )
            embed_compilation = st.checkbox(
                "Compilation",
                value=config.get("embed_compilation", False),
                key="embed_compilation",
            )
            embed_lyrics = st.checkbox(
                "Lyrics",
                value=config.get("embed_lyrics", False),
                key="embed_lyrics",
            )

        col_m5, col_m6 = st.columns(2)
        with col_m5:
            embed_explicit = st.checkbox(
                "Explicit",
                value=config.get("embed_explicit", False),
                key="embed_explicit",
            )
            embed_upc = st.checkbox(
                "UPC",
                value=config.get("embed_upc", False),
                key="embed_upc",
            )
            embed_service_id = st.checkbox(
                "Service ID",
                value=config.get("embed_service_id", False),
                key="embed_service_id",
            )
        with col_m6:
            embed_timesignature = st.checkbox(
                "Time signature",
                value=config.get("embed_timesignature", False),
                key="embed_timesignature",
            )
            embed_acousticness = st.checkbox(
                "Acousticness",
                value=config.get("embed_acousticness", False),
                key="embed_acousticness",
            )
            embed_danceability = st.checkbox(
                "Danceability",
                value=config.get("embed_danceability", False),
                key="embed_danceability",
            )
            embed_energy = st.checkbox(
                "Energy",
                value=config.get("embed_energy", False),
                key="embed_energy",
            )
            embed_instrumentalness = st.checkbox(
                "Instrumentalness",
                value=config.get("embed_instrumentalness", False),
                key="embed_instrumentalness",
            )
            embed_liveness = st.checkbox(
                "Liveness",
                value=config.get("embed_liveness", False),
                key="embed_liveness",
            )
            embed_loudness = st.checkbox(
                "Loudness",
                value=config.get("embed_loudness", False),
                key="embed_loudness",
            )
            embed_speechiness = st.checkbox(
                "Speechiness",
                value=config.get("embed_speechiness", False),
                key="embed_speechiness",
            )
            embed_valence = st.checkbox(
                "Valence",
                value=config.get("embed_valence", False),
                key="embed_valence",
            )

    # --- Video Downloads Tab ---
    with video_tab:
        st.subheader("Video download settings")

        video_download_path = st.text_input(
            "Video download path",
            value=config.get("video_download_path", ""),
            key="video_download_path",
        )

        col_v1, col_v2 = st.columns(2)
        with col_v1:
            movie_file_format = st.text_input(
                "Movie file format",
                value=config.get("movie_file_format", "{movie_name}"),
                key="movie_file_format",
            )
            movie_path_formatter = st.text_input(
                "Movie path formatter",
                value=config.get("movie_path_formatter", "{movie_name}"),
                key="movie_path_formatter",
            )
            show_file_format = st.text_input(
                "Show file format",
                value=config.get("show_file_format", "{show_name}"),
                key="show_file_format",
            )
        with col_v2:
            show_path_formatter = st.text_input(
                "Show path formatter",
                value=config.get("show_path_formatter", "{show_name}"),
                key="show_path_formatter",
            )
            preferred_video_resolution = st.number_input(
                "Preferred video resolution (p)",
                min_value=144,
                max_value=4320,
                value=config.get("preferred_video_resolution", 1080),
                step=1,
                key="preferred_video_resolution",
            )
            download_subtitles = st.checkbox(
                "Download subtitles",
                value=config.get("download_subtitles", False),
                key="download_subtitles",
            )

        col_v3, col_v4 = st.columns(2)
        with col_v3:
            preferred_audio_language = st.text_input(
                "Preferred audio language",
                value=config.get("preferred_audio_language", ""),
                key="preferred_audio_language",
            )
        with col_v4:
            preferred_subtitle_language = st.text_input(
                "Preferred subtitle language",
                value=config.get("preferred_subtitle_language", ""),
                key="preferred_subtitle_language",
            )

        col_v5, col_v6 = st.columns(2)
        with col_v5:
            download_all_available_audio = st.checkbox(
                "Download all available audio tracks",
                value=config.get("download_all_available_audio", False),
                key="download_all_available_audio",
            )
        with col_v6:
            download_all_available_subtitles = st.checkbox(
                "Download all available subtitles",
                value=config.get("download_all_available_subtitles", False),
                key="download_all_available_subtitles",
            )

    # --- Save all settings (mirrors Qt save_config) ---
    st.markdown("---")
    if st.button("💾 Save Settings", type="primary", use_container_width=True):
        # General Settings
        config.set("language", language)
        config.set("explicit_label", explicit_label)
        config.set("accent_color", accent_color)
        config.set("download_copy_btn", download_copy_btn)
        config.set("download_open_btn", download_open_btn)
        config.set("download_locate_btn", download_locate_btn)
        config.set("download_delete_btn", download_delete_btn)
        config.set("show_search_thumbnails", show_search_thumbnails)
        config.set("show_download_thumbnails", show_download_thumbnails)
        config.set("thumbnail_size", int(thumbnail_size))
        config.set("max_search_results", int(max_search_results))
        config.set("disable_download_popups", disable_download_popups)
        config.set(
            "windows_10_explorer_thumbnails",
            windows_10_explorer_thumbnails,
        )
        config.set("mirror_spotify_playback", mirror_spotify_playback)
        config.set("stealth_mode_enabled", stealth_mode_enabled)
        config.set("close_to_tray", close_to_tray)
        config.set("check_for_updates", check_for_updates)
        config.set("illegal_character_replacement", illegal_character_replacement)
        config.set("raw_media_download", raw_media_download)
        config.set("rotate_active_account_number", rotate_active_account_number)
        config.set("download_delay", int(download_delay))
        config.set("download_chunk_size", int(download_chunk_size))
        config.set("maximum_queue_workers", int(maximum_queue_workers))
        config.set("maximum_download_workers", int(maximum_download_workers))
        config.set("enable_retry_worker", enable_retry_worker)
        config.set("retry_worker_delay", int(retry_worker_delay))

        # Search Settings
        config.set("enable_search_tracks", enable_search_tracks)
        config.set("enable_search_albums", enable_search_albums)
        config.set("enable_search_playlists", enable_search_playlists)
        config.set("enable_search_artists", enable_search_artists)
        config.set("enable_search_episodes", enable_search_episodes)
        config.set("enable_search_podcasts", enable_search_podcasts)
        config.set("enable_search_audiobooks", enable_search_audiobooks)

        # Download Queue Filter Settings
        config.set("download_queue_show_waiting", dq_show_waiting)
        config.set("download_queue_show_failed", dq_show_failed)
        config.set("download_queue_show_cancelled", dq_show_cancelled)
        config.set("download_queue_show_unavailable", dq_show_unavailable)
        config.set("download_queue_show_completed", dq_show_completed)

        # Audio Download Settings
        config.set("audio_download_path", audio_download_path)
        config.set("track_file_format", track_file_format)
        config.set("track_path_formatter", track_path_formatter)
        config.set("podcast_file_format", podcast_file_format)
        config.set("podcast_path_formatter", podcast_path_formatter)
        config.set("use_playlist_path", use_playlist_path)
        config.set("playlist_path_formatter", playlist_path_formatter)
        config.set("create_m3u_file", create_m3u_file)
        config.set("m3u_path_formatter", m3u_path_formatter)
        config.set("extinf_separator", extinf_separator)
        config.set("extinf_label", extinf_label)
        config.set("save_album_cover", save_album_cover)
        config.set("album_cover_format", album_cover_format)
        config.set("file_bitrate", file_bitrate)
        config.set("file_hertz", int(file_hertz))
        config.set("use_custom_file_bitrate", use_custom_file_bitrate)
        config.set("download_lyrics", download_lyrics)
        config.set("only_download_synced_lyrics", only_download_synced_lyrics)
        config.set("only_download_plain_lyrics", only_download_plain_lyrics)
        config.set("save_lrc_file", save_lrc_file)
        config.set("translate_file_path", translate_file_path)

        # Legacy / CLI-related audio settings
        config.set("download_root", download_root)
        config.set("media_format", media_format)
        config.set("download_quality", download_quality)

        # Audio Metadata Settings
        config.set("metadata_separator", metadata_separator)
        config.set("overwrite_existing_metadata", overwrite_existing_metadata)
        config.set("embed_branding", embed_branding)
        config.set("embed_cover", embed_cover)
        config.set("embed_artist", embed_artist)
        config.set("embed_album", embed_album)
        config.set("embed_albumartist", embed_albumartist)
        config.set("embed_name", embed_name)
        config.set("embed_year", embed_year)
        config.set("embed_discnumber", embed_discnumber)
        config.set("embed_tracknumber", embed_tracknumber)
        config.set("embed_genre", embed_genre)
        config.set("embed_performers", embed_performers)
        config.set("embed_producers", embed_producers)
        config.set("embed_writers", embed_writers)
        config.set("embed_label", embed_label)
        config.set("embed_copyright", embed_copyright)
        config.set("embed_description", embed_description)
        config.set("embed_language", embed_language)
        config.set("embed_isrc", embed_isrc)
        config.set("embed_length", embed_length)
        config.set("embed_url", embed_url)
        config.set("embed_key", embed_key)
        config.set("embed_bpm", embed_bpm)
        config.set("embed_compilation", embed_compilation)
        config.set("embed_lyrics", embed_lyrics)
        config.set("embed_explicit", embed_explicit)
        config.set("embed_upc", embed_upc)
        config.set("embed_service_id", embed_service_id)
        config.set("embed_timesignature", embed_timesignature)
        config.set("embed_acousticness", embed_acousticness)
        config.set("embed_danceability", embed_danceability)
        config.set("embed_energy", embed_energy)
        config.set("embed_instrumentalness", embed_instrumentalness)
        config.set("embed_liveness", embed_liveness)
        config.set("embed_loudness", embed_loudness)
        config.set("embed_speechiness", embed_speechiness)
        config.set("embed_valence", embed_valence)

        # Video Download Settings
        config.set("video_download_path", video_download_path)
        config.set("movie_file_format", movie_file_format)
        config.set("movie_path_formatter", movie_path_formatter)
        config.set("show_file_format", show_file_format)
        config.set("show_path_formatter", show_path_formatter)
        config.set("preferred_video_resolution", int(preferred_video_resolution))
        config.set("download_subtitles", download_subtitles)
        config.set("preferred_audio_language", preferred_audio_language)
        config.set("preferred_subtitle_language", preferred_subtitle_language)
        config.set("download_all_available_audio", download_all_available_audio)
        config.set(
            "download_all_available_subtitles", download_all_available_subtitles
        )

        config.save()
        st.success("✅ Settings saved.")
        # Style hot-reload equivalent: rerun app so new theme/accent apply immediately
        st.rerun()


def render_about_page() -> None:
    """Render the ℹ️ About page."""

    st.header("ℹ️ About OnTheSpot")

    # Version and stats
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Version Information")
        st.info(f"**Version:** {config.get('version', 'Unknown')}")
        st.info("**UI:** Streamlit")

        st.subheader("Download Statistics")
        st.metric("Total Downloads", config.get("total_downloaded_items", 0))
        st.metric(
            "Total Data", format_bytes(config.get("total_downloaded_data", 0))
        )

    with col2:
        st.subheader("Supported Services")
        services = [
            "🎵 Spotify",
            "🎵 YouTube Music",
            "🎵 Apple Music",
            "🎵 SoundCloud",
            "🎵 Bandcamp",
            "🎵 Deezer",
            "🎵 Qobuz",
            "🎵 Tidal",
            "📺 Crunchyroll",
        ]
        for service in services:
            st.write(service)

    st.divider()

    st.subheader("About")
    st.markdown(
        """
		**OnTheSpot** is an easy-to-use music downloader written in Python. It supports various music services
		and downloads files and metadata directly from the service of your choosing.

		This is the **Streamlit UI** - a modern, web-based interface built with Streamlit.

		**Other Available UIs:**
		- 🖥️ PyQt6 GUI (Desktop Application)
		- 🌐 Flask Web UI
		- 💻 CLI (Command Line Interface)

		**GitHub:** [justin025/onthespot](https://github.com/justin025/onthespot)
		"""
    )

    st.divider()

    # System information
    with st.expander("📊 System Information"):
        st.write(f"**Config Directory:** {config_dir()}")
        st.write(f"**Cache Directory:** {cache_dir()}")
        st.write(f"**Download Directory:** {config.get('download_root', 'Not set')}")
        st.write(f"**Active Accounts:** {len(account_pool)}")
        st.write(f"**Queue Workers:** {config.get('maximum_queue_workers', 2)}")
        st.write(f"**Download Workers:** {config.get('maximum_download_workers', 4)}")


# Initialize session state
if "core_initialized" not in st.session_state:
    st.session_state.core_initialized = False
    st.session_state.auto_refresh = True
    st.session_state.refresh_interval = 2

# Initialize workers and accounts on first run
if not st.session_state.core_initialized:
    with st.spinner("Initializing OnTheSpot..."):
        initialize_workers()
        reload_accounts_from_config()
        st.session_state.core_initialized = True

# Main header
st.markdown('<div class="main-header">🎵 OnTheSpot - Streamlit UI</div>', unsafe_allow_html=True)

# Global status bar (mirrors PyQt main window status bar)
render_status_bar()

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["🔍 Search", "📥 Download Queue", "⚙️ Settings", "ℹ️ About"])

# Auto-refresh toggle
st.sidebar.markdown("---")
st.sidebar.subheader("Auto-Refresh")
st.session_state.auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh", value=st.session_state.auto_refresh)
if st.session_state.auto_refresh:
    st.session_state.refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 1, 10, st.session_state.refresh_interval)

# Display account info
st.sidebar.markdown("---")
st.sidebar.subheader("Active Account")
if len(account_pool) > 0:
    active_index = config.get('active_account_number', 0)
    if active_index >= len(account_pool):
        active_index = 0
    active_account = account_pool[active_index]
    st.sidebar.success(f"Service: {active_account['service'].replace('_', ' ').title()}")
else:
    st.sidebar.warning("No accounts configured")


# Page routing
if page == "🔍 Search":
    # Delegate to dedicated page renderer for Search
    render_search_page()

elif page == "📥 Download Queue":
    # Delegate to dedicated page renderer for Download Queue
    render_download_queue_page()

elif page == "⚙️ Settings":
    # Delegate to dedicated page renderer for Settings
    render_settings_page()

elif page == "ℹ️ About":
    # Delegate to dedicated page renderer for About
    render_about_page()

def _legacy_streamlit_settings_page_unused() -> None:
    """Legacy inline Settings page kept for reference; superseded by render_settings_page()."""

    '''
    st.header("⚙️ Settings")

    # Settings are organized to mirror the PyQt Settings dialog structure
    accounts_tab, general_tab, search_tab, queue_tab, audio_tab, metadata_tab, video_tab = st.tabs(
        ["Accounts", "General", "Search", "Download Queue", "Audio Downloads", "Audio Metadata", "Video Downloads"]
    )

    # --- Accounts Tab ---
    with accounts_tab:
        st.subheader("Accounts")

        # Read configured accounts from config and overlay runtime status from account_pool
        try:
            accounts_cfg = config.get("accounts", []).copy()
        except Exception:
            accounts_cfg = []

        if not accounts_cfg:
            st.info("No accounts configured in config.")
        else:
            account_rows = []
            for acc in accounts_cfg:
                uuid = acc.get("uuid", "-")
                service = acc.get("service", "-")
                active_cfg = acc.get("active", True)

                runtime = next((a for a in account_pool if a.get("uuid") == uuid), None)

                if runtime is not None:
                    username = runtime.get("username") or acc.get("login", {}).get("username") or "-"
                    account_type = str(runtime.get("account_type", acc.get("account_type", "-"))).title()
                    bitrate = runtime.get("bitrate", acc.get("bitrate", "-"))
                    status = str(runtime.get("status", "active")).title()
                else:
                    username = acc.get("login", {}).get("username") or acc.get("username") or "-"
                    account_type = str(acc.get("account_type", "-")).title()
                    bitrate = acc.get("bitrate", "-")
                    status = "Not Loaded"

                account_rows.append(
                    {
                        "UUID": uuid,
                        "Username": username,
                        "Service": service.replace("_", " ").title(),
                        "Active (config)": "Yes" if active_cfg else "No",
                        "Bitrate": bitrate,
                        "Status": status,
                    }
                )

            if account_rows:
                df_accounts = pd.DataFrame(account_rows)
                st.dataframe(df_accounts, use_container_width=True, hide_index=True)

        # Active account selection (mirrors Qt radio buttons, uses runtime pool)
        if len(account_pool) > 0:
            current_active = config.get("active_account_number", 0)
            if current_active < 0 or current_active >= len(account_pool):
                current_active = 0

            def _format_account_option(i: int) -> str:
                acc = account_pool[i]
                username = acc.get("username", "Unknown")
                service = acc.get("service", "-").replace("_", " ").title()
                return f"{i}: {username} ({service})"

            selected_active = st.radio(
                "Active account",
                options=list(range(len(account_pool))),
                index=current_active,
                format_func=_format_account_option,
                key="accounts_active_radio",
            )

            if selected_active != current_active:
                config.set("active_account_number", selected_active)
                config.save()
                st.success("Active account updated.")
        else:
            st.info("No active accounts in runtime pool (logins may have failed).")

        # Remove accounts from config and reload runtime pool
        if accounts_cfg:
            st.markdown("---")
            st.subheader("Remove accounts")

            for idx, acc in enumerate(accounts_cfg):
                uuid = acc.get("uuid", "-")
                runtime = next((a for a in account_pool if a.get("uuid") == uuid), None)

                if runtime is not None:
                    username = runtime.get("username", "Unknown")
                    service_name = runtime.get("service", "-").replace("_", " ").title()
                    status_text = str(runtime.get("status", "unknown")).title()
                else:
                    username = acc.get("login", {}).get("username") or acc.get("username") or "Unknown"
                    service_name = acc.get("service", "-").replace("_", " ").title()
                    status_text = "Not Loaded"

                col_a, col_b, col_c = st.columns([4, 4, 2])
                with col_a:
                    st.write(f"{idx}: {username} ({service_name})")
                with col_b:
                    st.write(status_text)
                with col_c:
                    if st.button("Remove", key=f"remove_account_{idx}"):
                        new_cfg = [a for j, a in enumerate(accounts_cfg) if j != idx]
                        config.set("accounts", new_cfg)
                        config.save()
                        reload_accounts_from_config()
                        st.success("Account removed. Accounts reloaded from config.")
                        st.rerun()

        # --- Add / login accounts (mirror Qt's set_login_fields & add_* helpers) ---
        st.markdown("---")
        st.subheader("Add account")

        service_labels = [
            "Apple Music",
            "Bandcamp",
            "Deezer",
            "Qobuz",
            "SoundCloud",
            "Spotify",
            "Tidal",
            "YouTube Music",
            "Crunchyroll",
            "Generic (yt-dlp)",
        ]
        service_codes = {
            "Apple Music": "apple_music",
            "Bandcamp": "bandcamp",
            "Deezer": "deezer",
            "Qobuz": "qobuz",
            "SoundCloud": "soundcloud",
            "Spotify": "spotify",
            "Tidal": "tidal",
            "YouTube Music": "youtube_music",
            "Crunchyroll": "crunchyroll",
            "Generic (yt-dlp)": "generic",
        }

        selected_service_label = st.selectbox(
            "Service",
            options=service_labels,
            key="accounts_add_service",
        )

        service_code = service_codes.get(selected_service_label)

        # Apple Music
        if service_code == "apple_music":
            media_user_token = st.text_input(
                "Media User Token",
                value="",
                type="password",
                help="Enter your Apple Music media-user-token",
                key="apple_music_media_user_token",
            )
            if st.button("Add Apple Music account", key="btn_add_apple_music"):
                token = media_user_token.strip()
                if not token:
                    st.error("Media User Token is required.")
                else:
                    try:
                        apple_music_add_account(token)
                        reload_accounts_from_config()
                        st.success("Apple Music account added and loaded.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to add Apple Music account: {e}")

        # Bandcamp
        elif service_code == "bandcamp":
            st.info(
                "Public Bandcamp account will be used. "
                "Logging into personal Bandcamp accounts is currently unsupported."
            )
            if st.button("Add Bandcamp account", key="btn_add_bandcamp"):
                try:
                    bandcamp_add_account()
                    reload_accounts_from_config()
                    st.success(
                        "Public Bandcamp account added and loaded. "
                        "If you have premium purchases, consider supporting the dev team."
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add Bandcamp account: {e}")

        # Deezer
        elif service_code == "deezer":
            arl = st.text_input(
                "ARL",
                value="",
                type="password",
                help="Enter your Deezer ARL cookie value",
                key="deezer_arl",
            )
            if st.button("Add Deezer account", key="btn_add_deezer"):
                arl_val = arl.strip()
                if not arl_val:
                    st.error("ARL is required.")
                else:
                    try:
                        deezer_add_account(arl_val)
                        reload_accounts_from_config()
                        st.success("Deezer account added and loaded.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to add Deezer account: {e}")

        # Qobuz
        elif service_code == "qobuz":
            email = st.text_input(
                "Email",
                value="",
                key="qobuz_email",
            )
            password = st.text_input(
                "Password",
                value="",
                type="password",
                key="qobuz_password",
            )
            if st.button("Add Qobuz account", key="btn_add_qobuz"):
                if not email.strip() or not password:
                    st.error("Email and password are required.")
                else:
                    try:
                        qobuz_add_account(email.strip(), password)
                        reload_accounts_from_config()
                        st.success("Qobuz account added and loaded.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to add Qobuz account: {e}")

        # SoundCloud
        elif service_code == "soundcloud":
            oauth_token = st.text_input(
                "OAuth Token",
                value="",
                type="password",
                help="Enter your SoundCloud oauth_token",
                key="soundcloud_oauth",
            )
            if st.button("Add SoundCloud account", key="btn_add_soundcloud"):
                token_val = oauth_token.strip()
                if not token_val:
                    st.error("OAuth token is required.")
                else:
                    try:
                        soundcloud_add_account(oauth_token=token_val)
                        reload_accounts_from_config()
                        st.success("SoundCloud account added and loaded.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to add SoundCloud account: {e}")

        # Spotify (zeroconf login via background worker)
        elif service_code == "spotify":
            st.info(
                "Starts a Zeroconf login service. "
                "Then, in the Spotify desktop app, select 'OnTheSpot' under devices to authorise."
            )
            if st.button("Start Spotify login", key="btn_add_spotify"):

                def _spotify_worker():
                    try:
                        if spotify_new_session():
                            logger.info("Spotify account added via Streamlit; please restart the app.")
                        else:
                            logger.info("Spotify account already exists; no new account added.")
                    except Exception as e:
                        logger.error(f"Spotify login worker failed: {e}")

                threading.Thread(target=_spotify_worker, daemon=True).start()
                st.success(
                    "Spotify login service started. "
                    "Open the Spotify desktop app and select 'OnTheSpot' as the device. "
                    "After login completes, restart OnTheSpot or reload this page."
                )

        # Tidal (device code login)
        elif service_code == "tidal":
            st.info(
                "Starts the Tidal device login flow. "
                "You will be given a URL to visit and authorise this device."
            )
            if st.button("Start Tidal login", key="btn_start_tidal"):
                try:
                    device_code, verification_url = tidal_add_account_pt1()
                except Exception as e:
                    st.error(f"Failed to start Tidal login: {e}")
                else:
                    st.markdown(
                        f"Go to **https://{verification_url}** in your browser to continue the Tidal login."
                    )

                    def _tidal_worker(code: str) -> None:
                        try:
                            if tidal_add_account_pt2(code):
                                logger.info("Tidal account added via Streamlit; please restart the app.")
                            else:
                                logger.info("Tidal account already exists; no new account added.")
                        except Exception as exc:
                            logger.error(f"Tidal login worker failed: {exc}")

                    threading.Thread(target=_tidal_worker, args=(device_code,), daemon=True).start()
                    st.success(
                        "Tidal login started. Complete the login in your browser, "
                        "then restart OnTheSpot or reload this page."
                    )

        # YouTube Music
        elif service_code == "youtube_music":
            st.info("Adds a public YouTube Music account using yt-dlp.")
            if st.button("Add YouTube Music account", key="btn_add_ytmusic"):
                try:
                    youtube_music_add_account()
                    reload_accounts_from_config()
                    st.success("Public YouTube Music account added and loaded.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add YouTube Music account: {e}")

        # Crunchyroll
        elif service_code == "crunchyroll":
            email = st.text_input(
                "Email",
                value="",
                key="crunchy_email",
            )
            password = st.text_input(
                "Password",
                value="",
                type="password",
                key="crunchy_password",
            )
            if st.button("Add Crunchyroll account", key="btn_add_crunchy"):
                if not email.strip() or not password:
                    st.error("Email and password are required.")
                else:
                    try:
                        crunchyroll_add_account(email.strip(), password)
                        reload_accounts_from_config()
                        st.success("Crunchyroll account added and loaded.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to add Crunchyroll account: {e}")

        # Generic (yt-dlp)
        elif service_code == "generic":
            try:
                extractors = generic_list_extractors()
            except Exception as e:
                extractors = []
                logger.error(f"Failed to list generic extractors: {e}")
            if extractors:
                st.markdown(
                    "The following services are officially supported by the generic downloader:"\
                    "<br>" + "<br>".join(extractors),
                    unsafe_allow_html=True,
                )
            if st.button("Add Generic downloader", key="btn_add_generic"):
                try:
                    generic_add_account()
                    reload_accounts_from_config()
                    st.success("Generic downloader added and loaded.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add Generic downloader: {e}")

        st.markdown("---")
        if st.button("Reload accounts from config", key="btn_reload_accounts"):
            reload_accounts_from_config()
            st.success("Accounts reloaded from config.")
            st.rerun()

        # --- General Tab ---
        with general_tab:
            st.subheader("General settings")


            # Language
            language_options = ["English", "Deutsch", "Português"]
            current_language = config.get("language", "English")
            try:
                lang_index = language_options.index(current_language)
            except ValueError:
                lang_index = 0

            language = st.selectbox(
                "Language",
                language_options,
                index=lang_index,
                key="general_language",
            )
            explicit_label = st.text_input(
                "Explicit label",
                value=config.get("explicit_label", "Explicit"),
                key="general_explicit_label",
            )

            # Appearance / theme (shared accent color with Qt)
            current_accent = config.get("accent_color", get_accent_color())
            accent_color = st.color_picker(
                "Accent color",
                value=current_accent,
                key="general_accent_color",
                help="Primary accent color used across all UIs (Qt and Streamlit)",
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                download_copy_btn = st.checkbox(
                    "Show Copy button",
                    value=config.get("download_copy_btn", True),
                    key="general_download_copy_btn",
                )
                download_open_btn = st.checkbox(
                    "Show Open button",
                    value=config.get("download_open_btn", True),
                    key="general_download_open_btn",
                )
            with col2:
                download_locate_btn = st.checkbox(
                    "Show Locate button",
                    value=config.get("download_locate_btn", True),
                    key="general_download_locate_btn",
                )
                download_delete_btn = st.checkbox(
                    "Show Delete button",
                    value=config.get("download_delete_btn", False),
                    key="general_download_delete_btn",
                )
            with col3:
                show_search_thumbnails = st.checkbox(
                    "Show search thumbnails",
                    value=config.get("show_search_thumbnails", True),
                    key="general_show_search_thumbnails",
                )
                show_download_thumbnails = st.checkbox(
                    "Show download thumbnails",
                    value=config.get("show_download_thumbnails", True),
                    key="general_show_download_thumbnails",
                )

            col4, col5, col6 = st.columns(3)
            with col4:
                thumbnail_size = st.number_input(
                    "Thumbnail size",
                    min_value=32,
                    max_value=512,
                    value=config.get("thumbnail_size", 128),
                    step=1,
                    key="general_thumbnail_size",
                )
            with col5:
                max_search_results = st.number_input(
                    "Max search results",
                    min_value=1,
                    max_value=1000,
                    value=config.get("max_search_results", 50),
                    step=1,
                    key="general_max_search_results",
                )
            with col6:
                disable_download_popups = st.checkbox(
                    "Disable download popups",
                    value=config.get("disable_download_popups", False),
                    key="general_disable_download_popups",
                )

            col7, col8, col9 = st.columns(3)
            with col7:
                windows_10_explorer_thumbnails = st.checkbox(
                    "Windows Explorer thumbnails",
                    value=config.get("windows_10_explorer_thumbnails", False),
                    key="general_win_thumb",
                )
                mirror_spotify_playback = st.checkbox(
                    "Mirror Spotify playback",
                    value=config.get("mirror_spotify_playback", False),
                    key="general_mirror_spotify",
                )
            with col8:
                stealth_mode_enabled = st.checkbox(
                    "Enable Stealth mode",
                    value=config.get("stealth_mode_enabled", False),
                    key="general_stealth_mode",
                )
                close_to_tray = st.checkbox(
                    "Close to tray",
                    value=config.get("close_to_tray", False),
                    key="general_close_to_tray",
                )
            with col9:
                check_for_updates = st.checkbox(
                    "Check for updates",
                    value=config.get("check_for_updates", True),
                    key="general_check_for_updates",
                )
                raw_media_download = st.checkbox(
                    "Raw media download",
                    value=config.get("raw_media_download", False),
                    key="general_raw_media_download",
                )

            col10, col11 = st.columns(2)
            with col10:
                illegal_character_replacement = st.text_input(
                    "Illegal character replacement",
                    value=config.get("illegal_character_replacement", "_"),
                    key="general_illegal_characters",
                )
            with col11:
                rotate_active_account_number = st.checkbox(
                    "Rotate active account for metadata",
                    value=config.get("rotate_active_account_number", False),
                    key="general_rotate_active",
                )

            st.markdown("---")
            st.subheader("Workers & performance")

            colw1, colw2, colw3 = st.columns(3)
        with colw1:
            download_delay = st.number_input(
                "Download delay (ms)",
                min_value=0,
                max_value=10000,
                value=config.get("download_delay", 0),
                step=50,
                key="general_download_delay",
            )
        with colw2:
            # Chunk size is stored and used as bytes in the backend (downloader.py / Qt settings)
            # Use bytes here too, with a wide safe range, to avoid Streamlit max_value errors.
            _raw_chunk = int(config.get("download_chunk_size", 65536))
            _raw_chunk = max(1024, min(1048576, _raw_chunk))
            download_chunk_size = st.number_input(
                "Download chunk size (bytes)",
                min_value=1024,
                max_value=1_048_576,
                value=_raw_chunk,
                step=1024,
                key="general_download_chunk",
            )
        with colw3:
            maximum_queue_workers = st.number_input(
                "Max queue workers",
                min_value=1,
                max_value=16,
                value=config.get("maximum_queue_workers", 2),
                step=1,
                key="general_queue_workers",
            )

        colw4, colw5 = st.columns(2)
        with colw4:
            maximum_download_workers = st.number_input("Max download workers", min_value=1, max_value=16, value=config.get("maximum_download_workers", 4), step=1, key="general_download_workers")
        with colw5:
            enable_retry_worker = st.checkbox("Enable retry worker", value=config.get("enable_retry_worker", False), key="general_retry_worker")
            retry_worker_delay = st.number_input("Retry worker delay (s)", min_value=1, max_value=3600, value=config.get("retry_worker_delay", 30), step=1, key="general_retry_delay")

        st.markdown("---")
        st.subheader("Maintenance")
        tool_col1, tool_col2 = st.columns(2)
        with tool_col1:
            confirm_clear = st.checkbox(
                "I understand this will delete cached requests and logs",
                key="confirm_clear_cache",
            )
            if st.button("Clear cache"):
                if not confirm_clear:
                    notify(
                        "Please confirm you want to clear the cache by ticking the box above.",
                        level="warning",
                    )
                else:
                    reqcache_path = os.path.join(cache_dir(), "reqcache")
                    logs_path = os.path.join(cache_dir(), "logs")
                    try:
                        shutil.rmtree(reqcache_path, ignore_errors=True)
                        shutil.rmtree(logs_path, ignore_errors=True)
                        notify(
                            f"Cache cleared.\n\nDeleted:\n- {reqcache_path}\n- {logs_path}",
                            level="success",
                        )
                    except Exception as e:
                        notify(f"Failed to clear cache: {e}", level="error")
        with tool_col2:
            if st.button("Export logs to Downloads"):
                logs_src = os.path.join(
                    cache_dir(),
                    "logs",
                    getattr(config, "session_uuid", ""),
                    "onthespot.log",
                )
                dst_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                dst_path = os.path.join(dst_dir, "onthespot.log")
                try:
                    if not os.path.isfile(logs_src):
                        notify(
                            f"No log file found for this session at: {logs_src}",
                            level="error",
                        )
                    else:
                        os.makedirs(dst_dir, exist_ok=True)
                        shutil.copy(logs_src, dst_path)
                        notify(
                            f"Logs exported to '{dst_path}'",
                            level="success",
                        )
                except Exception as e:
                    notify(f"Failed to export logs: {e}", level="error")

    # --- Search Tab ---
    with search_tab:
        st.subheader("Search")

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            enable_search_tracks = st.checkbox(
                "Tracks", value=config.get("enable_search_tracks"), key="search_tracks"
            )
            enable_search_albums = st.checkbox(
                "Albums", value=config.get("enable_search_albums"), key="search_albums"
            )
            enable_search_playlists = st.checkbox(
                "Playlist", value=config.get("enable_search_playlists"), key="search_playlists"
            )
        with col_s2:
            enable_search_artists = st.checkbox(
                "Artists", value=config.get("enable_search_artists"), key="search_artists"
            )
            enable_search_episodes = st.checkbox(
                "Episodes", value=config.get("enable_search_episodes"), key="search_episodes"
            )
            enable_search_podcasts = st.checkbox(
                "Podcasts", value=config.get("enable_search_podcasts"), key="search_podcasts"
            )
            enable_search_audiobooks = st.checkbox(
                "Audiobooks", value=config.get("enable_search_audiobooks"), key="search_audiobooks"
            )

    # --- Download Queue Tab ---
    with queue_tab:
        st.subheader("Download queue filters")

        col_q1, col_q2, col_q3, col_q4, col_q5 = st.columns(5)
        with col_q1:
            dq_show_waiting = st.checkbox("Waiting", value=config.get("download_queue_show_waiting", True), key="dq_show_waiting")
        with col_q2:
            dq_show_failed = st.checkbox("Failed", value=config.get("download_queue_show_failed", True), key="dq_show_failed")
        with col_q3:
            dq_show_unavailable = st.checkbox("Unavailable", value=config.get("download_queue_show_unavailable", True), key="dq_show_unavailable")
        with col_q4:
            dq_show_cancelled = st.checkbox("Cancelled", value=config.get("download_queue_show_cancelled", True), key="dq_show_cancelled")
        with col_q5:
            dq_show_completed = st.checkbox("Completed", value=config.get("download_queue_show_completed", True), key="dq_show_completed")

    # --- Audio Downloads Tab ---
    with audio_tab:
        st.subheader("Audio download settings")

        audio_download_path = st.text_input("Audio download path", value=config.get("audio_download_path", ""), key="audio_download_path")

        col_a1, col_a2 = st.columns(2)
        with col_a1:
            track_file_format = st.text_input("Track file format", value=config.get("track_file_format", "{track_name}"), key="track_file_format")
            track_path_formatter = st.text_input("Track path formatter", value=config.get("track_path_formatter", "{artist}/{album}"), key="track_path_formatter")
            podcast_file_format = st.text_input("Podcast file format", value=config.get("podcast_file_format", "{episode_name}"), key="podcast_file_format")
            podcast_path_formatter = st.text_input("Podcast path formatter", value=config.get("podcast_path_formatter", "{show_name}"), key="podcast_path_formatter")
        with col_a2:
            use_playlist_path = st.checkbox("Use playlist path for playlist items", value=config.get("use_playlist_path", False), key="use_playlist_path")
            playlist_path_formatter = st.text_input("Playlist path formatter", value=config.get("playlist_path_formatter", "{playlist_name}"), key="playlist_path_formatter")
            create_m3u_file = st.checkbox("Create M3U file", value=config.get("create_m3u_file", False), key="create_m3u_file")
            m3u_path_formatter = st.text_input("M3U path formatter", value=config.get("m3u_path_formatter", "{playlist_name}.m3u"), key="m3u_path_formatter")

        col_a3, col_a4 = st.columns(2)
        with col_a3:
            extinf_separator = st.text_input("EXTINF separator", value=config.get("extinf_separator", " - "), key="extinf_separator")
            extinf_label = st.text_input("EXTINF label", value=config.get("extinf_label", "#EXTINF"), key="extinf_label")
            save_album_cover = st.checkbox("Save album cover", value=config.get("save_album_cover", True), key="save_album_cover")
        with col_a4:
            album_cover_format = st.text_input("Album cover format", value=config.get("album_cover_format", "jpg"), key="album_cover_format")
            file_bitrate = st.text_input("File bitrate (kbps)", value=config.get("file_bitrate", "320"), key="file_bitrate")
            file_hertz = st.number_input("Sample rate (Hz)", min_value=8000, max_value=192000, value=config.get("file_hertz", 44100), step=1000, key="file_hertz")

        col_a5, col_a6 = st.columns(2)
        with col_a5:
            use_custom_file_bitrate = st.checkbox("Use custom file bitrate", value=config.get("use_custom_file_bitrate", False), key="use_custom_file_bitrate")
            download_lyrics = st.checkbox("Download lyrics", value=config.get("download_lyrics", False), key="download_lyrics")
        with col_a6:
            only_download_synced_lyrics = st.checkbox("Only synced lyrics", value=config.get("only_download_synced_lyrics", False), key="only_synced_lyrics")
            only_download_plain_lyrics = st.checkbox("Only plain lyrics", value=config.get("only_download_plain_lyrics", False), key="only_plain_lyrics")
            save_lrc_file = st.checkbox("Save .lrc file", value=config.get("save_lrc_file", False), key="save_lrc_file")

        translate_file_path = st.checkbox("Translate file path to Latin characters", value=config.get("translate_file_path", False), key="translate_file_path")

        st.markdown("---")
        st.subheader("Legacy download root & format (CLI compatibility)")
        col_legacy1, col_legacy2, col_legacy3 = st.columns(3)
        with col_legacy1:
            download_root = st.text_input("Download root", value=config.get("download_root", ""), key="download_root")
        with col_legacy2:
            media_format = st.selectbox("Audio format", ["mp3", "ogg", "flac", "m4a"], index=["mp3", "ogg", "flac", "m4a"].index(config.get("media_format", "mp3")), key="media_format")
        with col_legacy3:
            download_quality = st.selectbox("Audio quality", ["low", "medium", "high", "very_high"], index=["low", "medium", "high", "very_high"].index(config.get("download_quality", "high")), key="download_quality")

    # --- Audio Metadata Tab ---
    with metadata_tab:
        st.subheader("Audio metadata settings")

        metadata_separator = st.text_input("Metadata separator", value=config.get("metadata_separator", " / "), key="metadata_separator")
        overwrite_existing_metadata = st.checkbox("Overwrite existing metadata", value=config.get("overwrite_existing_metadata", True), key="overwrite_metadata")

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            embed_branding = st.checkbox("Branding", value=config.get("embed_branding", True), key="embed_branding")
            embed_cover = st.checkbox("Cover", value=config.get("embed_cover", True), key="embed_cover")
            embed_artist = st.checkbox("Artist", value=config.get("embed_artist", True), key="embed_artist")
            embed_album = st.checkbox("Album", value=config.get("embed_album", True), key="embed_album")
            embed_albumartist = st.checkbox("Album artist", value=config.get("embed_albumartist", True), key="embed_albumartist")
            embed_name = st.checkbox("Track name", value=config.get("embed_name", True), key="embed_name")
        with col_m2:
            embed_year = st.checkbox("Year", value=config.get("embed_year", True), key="embed_year")
            embed_discnumber = st.checkbox("Disc number", value=config.get("embed_discnumber", True), key="embed_discnumber")
            embed_tracknumber = st.checkbox("Track number", value=config.get("embed_tracknumber", True), key="embed_tracknumber")
            embed_genre = st.checkbox("Genre", value=config.get("embed_genre", True), key="embed_genre")
            embed_performers = st.checkbox("Performers", value=config.get("embed_performers", False), key="embed_performers")
            embed_producers = st.checkbox("Producers", value=config.get("embed_producers", False), key="embed_producers")
        with col_m3:
            embed_writers = st.checkbox("Writers", value=config.get("embed_writers", False), key="embed_writers")
            embed_label = st.checkbox("Label", value=config.get("embed_label", False), key="embed_label")
            embed_copyright = st.checkbox("Copyright", value=config.get("embed_copyright", False), key="embed_copyright")
            embed_description = st.checkbox("Description", value=config.get("embed_description", False), key="embed_description")
            embed_language = st.checkbox("Language", value=config.get("embed_language", False), key="embed_language")
            embed_isrc = st.checkbox("ISRC", value=config.get("embed_isrc", False), key="embed_isrc")
        with col_m4:
            embed_length = st.checkbox("Length", value=config.get("embed_length", False), key="embed_length")
            embed_url = st.checkbox("URL", value=config.get("embed_url", False), key="embed_url")
            embed_key = st.checkbox("Key", value=config.get("embed_key", False), key="embed_key")
            embed_bpm = st.checkbox("BPM", value=config.get("embed_bpm", False), key="embed_bpm")
            embed_compilation = st.checkbox("Compilation", value=config.get("embed_compilation", False), key="embed_compilation")
            embed_lyrics = st.checkbox("Lyrics", value=config.get("embed_lyrics", False), key="embed_lyrics")

        col_m5, col_m6 = st.columns(2)
        with col_m5:
            embed_explicit = st.checkbox("Explicit", value=config.get("embed_explicit", False), key="embed_explicit")
            embed_upc = st.checkbox("UPC", value=config.get("embed_upc", False), key="embed_upc")
            embed_service_id = st.checkbox("Service ID", value=config.get("embed_service_id", False), key="embed_service_id")
        with col_m6:
            embed_timesignature = st.checkbox("Time signature", value=config.get("embed_timesignature", False), key="embed_timesignature")
            embed_acousticness = st.checkbox("Acousticness", value=config.get("embed_acousticness", False), key="embed_acousticness")
            embed_danceability = st.checkbox("Danceability", value=config.get("embed_danceability", False), key="embed_danceability")
            embed_energy = st.checkbox("Energy", value=config.get("embed_energy", False), key="embed_energy")
            embed_instrumentalness = st.checkbox("Instrumentalness", value=config.get("embed_instrumentalness", False), key="embed_instrumentalness")
            embed_liveness = st.checkbox("Liveness", value=config.get("embed_liveness", False), key="embed_liveness")
            embed_loudness = st.checkbox("Loudness", value=config.get("embed_loudness", False), key="embed_loudness")
            embed_speechiness = st.checkbox("Speechiness", value=config.get("embed_speechiness", False), key="embed_speechiness")
            embed_valence = st.checkbox("Valence", value=config.get("embed_valence", False), key="embed_valence")

    # --- Video Downloads Tab ---
    with video_tab:
        st.subheader("Video download settings")

        video_download_path = st.text_input("Video download path", value=config.get("video_download_path", ""), key="video_download_path")

        col_v1, col_v2 = st.columns(2)
        with col_v1:
            movie_file_format = st.text_input("Movie file format", value=config.get("movie_file_format", "{movie_name}"), key="movie_file_format")
            movie_path_formatter = st.text_input("Movie path formatter", value=config.get("movie_path_formatter", "{movie_name}"), key="movie_path_formatter")
            show_file_format = st.text_input("Show file format", value=config.get("show_file_format", "{show_name}"), key="show_file_format")
        with col_v2:
            show_path_formatter = st.text_input("Show path formatter", value=config.get("show_path_formatter", "{show_name}"), key="show_path_formatter")
            preferred_video_resolution = st.number_input("Preferred video resolution (p)", min_value=144, max_value=4320, value=config.get("preferred_video_resolution", 1080), step=1, key="preferred_video_resolution")
            download_subtitles = st.checkbox("Download subtitles", value=config.get("download_subtitles", False), key="download_subtitles")

        col_v3, col_v4 = st.columns(2)
        with col_v3:
            preferred_audio_language = st.text_input("Preferred audio language", value=config.get("preferred_audio_language", ""), key="preferred_audio_language")
        with col_v4:
            preferred_subtitle_language = st.text_input("Preferred subtitle language", value=config.get("preferred_subtitle_language", ""), key="preferred_subtitle_language")

        col_v5, col_v6 = st.columns(2)
        with col_v5:
            download_all_available_audio = st.checkbox("Download all available audio tracks", value=config.get("download_all_available_audio", False), key="download_all_available_audio")
        with col_v6:
            download_all_available_subtitles = st.checkbox("Download all available subtitles", value=config.get("download_all_available_subtitles", False), key="download_all_available_subtitles")

    # --- Save all settings (mirrors Qt save_config) ---
    st.markdown("---")
    if st.button("💾 Save Settings", type="primary", use_container_width=True):
        # General Settings
        config.set('language', language)
        config.set('explicit_label', explicit_label)
        config.set('accent_color', accent_color)
        config.set('download_copy_btn', download_copy_btn)
        config.set('download_open_btn', download_open_btn)
        config.set('download_locate_btn', download_locate_btn)
        config.set('download_delete_btn', download_delete_btn)
        config.set('show_search_thumbnails', show_search_thumbnails)
        config.set('show_download_thumbnails', show_download_thumbnails)
        config.set('thumbnail_size', int(thumbnail_size))
        config.set('max_search_results', int(max_search_results))
        config.set('disable_download_popups', disable_download_popups)
        config.set('windows_10_explorer_thumbnails', windows_10_explorer_thumbnails)
        config.set('mirror_spotify_playback', mirror_spotify_playback)
        config.set('stealth_mode_enabled', stealth_mode_enabled)
        config.set('close_to_tray', close_to_tray)
        config.set('check_for_updates', check_for_updates)
        config.set('illegal_character_replacement', illegal_character_replacement)
        config.set('raw_media_download', raw_media_download)
        config.set('rotate_active_account_number', rotate_active_account_number)
        config.set('download_delay', int(download_delay))
        config.set('download_chunk_size', int(download_chunk_size))
        config.set('maximum_queue_workers', int(maximum_queue_workers))
        config.set('maximum_download_workers', int(maximum_download_workers))
        config.set('enable_retry_worker', enable_retry_worker)
        config.set('retry_worker_delay', int(retry_worker_delay))

        # Search Settings
        config.set('enable_search_tracks', enable_search_tracks)
        config.set('enable_search_albums', enable_search_albums)
        config.set('enable_search_playlists', enable_search_playlists)
        config.set('enable_search_artists', enable_search_artists)
        config.set('enable_search_episodes', enable_search_episodes)
        config.set('enable_search_podcasts', enable_search_podcasts)
        config.set('enable_search_audiobooks', enable_search_audiobooks)

        # Download Queue Filter Settings
        config.set('download_queue_show_waiting', dq_show_waiting)
        config.set('download_queue_show_failed', dq_show_failed)
        config.set('download_queue_show_cancelled', dq_show_cancelled)
        config.set('download_queue_show_unavailable', dq_show_unavailable)
        config.set('download_queue_show_completed', dq_show_completed)

        # Audio Download Settings
        config.set('audio_download_path', audio_download_path)
        config.set('track_file_format', track_file_format)
        config.set('track_path_formatter', track_path_formatter)
        config.set('podcast_file_format', podcast_file_format)
        config.set('podcast_path_formatter', podcast_path_formatter)
        config.set('use_playlist_path', use_playlist_path)
        config.set('playlist_path_formatter', playlist_path_formatter)
        config.set('create_m3u_file', create_m3u_file)
        config.set('m3u_path_formatter', m3u_path_formatter)
        config.set('extinf_separator', extinf_separator)
        config.set('extinf_label', extinf_label)
        config.set('save_album_cover', save_album_cover)
        config.set('album_cover_format', album_cover_format)
        config.set('file_bitrate', file_bitrate)
        config.set('file_hertz', int(file_hertz))
        config.set('use_custom_file_bitrate', use_custom_file_bitrate)
        config.set('download_lyrics', download_lyrics)
        config.set('only_download_synced_lyrics', only_download_synced_lyrics)
        config.set('only_download_plain_lyrics', only_download_plain_lyrics)
        config.set('save_lrc_file', save_lrc_file)
        config.set('translate_file_path', translate_file_path)

        # Legacy / CLI-related audio settings
        config.set('download_root', download_root)
        config.set('media_format', media_format)
        config.set('download_quality', download_quality)

        # Audio Metadata Settings
        config.set('metadata_separator', metadata_separator)
        config.set('overwrite_existing_metadata', overwrite_existing_metadata)
        config.set('embed_branding', embed_branding)
        config.set('embed_cover', embed_cover)
        config.set('embed_artist', embed_artist)
        config.set('embed_album', embed_album)
        config.set('embed_albumartist', embed_albumartist)
        config.set('embed_name', embed_name)
        config.set('embed_year', embed_year)
        config.set('embed_discnumber', embed_discnumber)
        config.set('embed_tracknumber', embed_tracknumber)
        config.set('embed_genre', embed_genre)
        config.set('embed_performers', embed_performers)
        config.set('embed_producers', embed_producers)
        config.set('embed_writers', embed_writers)
        config.set('embed_label', embed_label)
        config.set('embed_copyright', embed_copyright)
        config.set('embed_description', embed_description)
        config.set('embed_language', embed_language)
        config.set('embed_isrc', embed_isrc)
        config.set('embed_length', embed_length)
        config.set('embed_url', embed_url)
        config.set('embed_key', embed_key)
        config.set('embed_bpm', embed_bpm)
        config.set('embed_compilation', embed_compilation)
        config.set('embed_lyrics', embed_lyrics)
        config.set('embed_explicit', embed_explicit)
        config.set('embed_upc', embed_upc)
        config.set('embed_service_id', embed_service_id)
        config.set('embed_timesignature', embed_timesignature)
        config.set('embed_acousticness', embed_acousticness)
        config.set('embed_danceability', embed_danceability)
        config.set('embed_energy', embed_energy)
        config.set('embed_instrumentalness', embed_instrumentalness)
        config.set('embed_liveness', embed_liveness)
        config.set('embed_loudness', embed_loudness)
        config.set('embed_speechiness', embed_speechiness)
        config.set('embed_valence', embed_valence)

        # Video Download Settings
        config.set('video_download_path', video_download_path)
        config.set('movie_file_format', movie_file_format)
        config.set('movie_path_formatter', movie_path_formatter)
        config.set('show_file_format', show_file_format)
        config.set('show_path_formatter', show_path_formatter)
        config.set('preferred_video_resolution', int(preferred_video_resolution))
        config.set('download_subtitles', download_subtitles)
        config.set('preferred_audio_language', preferred_audio_language)
        config.set('preferred_subtitle_language', preferred_subtitle_language)
        config.set('download_all_available_audio', download_all_available_audio)
        config.set('download_all_available_subtitles', download_all_available_subtitles)

	    config.save()
	    st.success("✅ Settings saved.")
	    # Style hot-reload equivalent: rerun app so new theme/accent apply immediately
	    st.rerun()

	# Footer
	st.sidebar.markdown("---")
	st.sidebar.caption("OnTheSpot Streamlit UI v1.0")
	st.sidebar.caption("Made with ❤️ using Streamlit")
	
	
	def main():
    """Main entry point for the Streamlit UI"""
    config.migration()
    logger.info(f'OnTheSpot Streamlit UI Version: {config.get("version")}')


	if __name__ == '__main__':
	    main()
	
	
    '''


# Footer
st.sidebar.markdown("---")
st.sidebar.caption("OnTheSpot Streamlit UI v1.0")
st.sidebar.caption("Made with ❤️ using Streamlit")


def main():
	"""Main entry point for the Streamlit UI."""
	config.migration()
	logger.info(f'OnTheSpot Streamlit UI Version: {config.get("version")}')


if __name__ == '__main__':
	main()