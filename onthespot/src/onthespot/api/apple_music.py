import base64
import json
import m3u8
from pathlib import Path
import requests
import re
import time
from uuid import uuid4
import xml.etree.ElementTree as ET
from pywidevine import PSSH, Cdm, Device
from pywidevine.license_protocol_pb2 import WidevinePsshData
from ..constants import WVN_KEY
from ..otsconfig import config
from ..runtimedata import account_pool, get_logger
from ..utils import conv_list_format, make_call

logger = get_logger("api.apple_music")
BASE_URL = 'https://amp-api.music.apple.com/v1'
WVN_LICENSE_URL = "https://play.itunes.apple.com/WebObjects/MZPlay.woa/wa/acquireWebPlaybackLicense"

# Constants for improved reliability
DEFAULT_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
TOKEN_EXPIRY_BUFFER = 300  # Refresh token 5 minutes before expiry


def _decode_jwt_payload(token):
    """Decode JWT token payload without verification (for expiry check only)."""
    try:
        # JWT format: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            return None

        # Decode payload (add padding if needed)
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding

        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        logger.debug(f"Failed to decode JWT: {e}")
        return None


def _is_token_expired(token):
    """Check if JWT token is expired or about to expire."""
    payload = _decode_jwt_payload(token)
    if not payload:
        return False  # Can't determine, assume valid

    exp = payload.get('exp')
    if not exp:
        return False  # No expiry, assume valid

    # Check if token expires within buffer time
    return time.time() > (exp - TOKEN_EXPIRY_BUFFER)


def _request_with_retry(session, method, url, max_retries=MAX_RETRIES, **kwargs):
    """Make HTTP request with retry logic and timeout."""
    kwargs.setdefault('timeout', DEFAULT_TIMEOUT)

    last_exception = None
    for attempt in range(max_retries):
        try:
            if method.upper() == 'GET':
                response = session.get(url, **kwargs)
            elif method.upper() == 'POST':
                response = session.post(url, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response
        except requests.exceptions.Timeout as e:
            last_exception = e
            logger.warning(f"Request timeout (attempt {attempt + 1}/{max_retries}): {url}")
        except requests.exceptions.ConnectionError as e:
            last_exception = e
            logger.warning(f"Connection error (attempt {attempt + 1}/{max_retries}): {url}")
        except requests.exceptions.HTTPError as e:
            # Don't retry on client errors (4xx)
            if e.response is not None and 400 <= e.response.status_code < 500:
                raise
            last_exception = e
            logger.warning(f"HTTP error (attempt {attempt + 1}/{max_retries}): {e}")

        if attempt < max_retries - 1:
            time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff

    raise last_exception or Exception(f"Request failed after {max_retries} attempts: {url}")


def apple_music_add_account(media_user_token):
    cfg_copy = config.get('accounts').copy()
    new_user = {
        "uuid": str(uuid4()),
        "service": "apple_music",
        "active": True,
        "login": {
            "media-user-token": media_user_token
        }
    }
    cfg_copy.append(new_user)
    config.set('accounts', cfg_copy)
    config.save()


def apple_music_login_user(account):
    logger.info('Logging into Apple Music account...')
    try:
        session = requests.Session()
        media_user_token = account['login']['media-user-token']

        if not media_user_token:
            raise ValueError("Media user token is empty. Please provide a valid token.")

        session.cookies.update({'media-user-token': media_user_token})
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
                "Accept": "application/json",
                "Accept-Language": 'en-US',
                "Accept-Encoding": "utf-8",
                "content-type": "application/json",
                "Media-User-Token": media_user_token,
                "x-apple-renewal": "true",
                "DNT": "1",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site",
                "origin": "https://music.apple.com",
            }
        )

        # Retrieve token from the homepage with timeout
        logger.debug("Fetching Apple Music homepage...")
        home_page = session.get("https://music.apple.com", timeout=DEFAULT_TIMEOUT).text

        # Extract JS bundle path
        js_match = re.search(r"/(assets/index-legacy[~-][^/]+\.js)", home_page)
        if not js_match:
            raise ValueError("Could not find Apple Music JavaScript bundle. Website structure may have changed.")

        index_js_uri = js_match.group(1)
        logger.debug(f"Found JS bundle: {index_js_uri}")

        index_js_page = session.get(f"https://music.apple.com/{index_js_uri}", timeout=DEFAULT_TIMEOUT).text

        # Extract Bearer token
        token_match = re.search('(?=eyJh)(.*?)(?=")', index_js_page)
        if not token_match:
            raise ValueError("Could not extract Bearer token from JavaScript bundle.")

        token = token_match.group(1)
        session.headers.update({"authorization": f"Bearer {token}"})
        session.params = {"l": 'en-US'}

        # Get account info
        logger.debug("Fetching account subscription info...")
        account_response = session.get(f'{BASE_URL}/me/account?meta=subscription', timeout=DEFAULT_TIMEOUT)

        if account_response.status_code == 401:
            raise ValueError("Invalid or expired media-user-token. Please get a new token from Apple Music website.")

        account_data = account_response.json()
        storefront = account_data.get('meta', {}).get('subscription', {}).get('storefront')

        if not storefront:
            logger.warning("Could not determine storefront, defaulting to 'us'")
            storefront = 'us'

        session.cookies.update({'itua': storefront})

        is_active = account_data.get('meta', {}).get('subscription', {}).get('active', False)
        account_type = "premium" if is_active else 'free'

        # Check if bearer token is about to expire
        if _is_token_expired(token):
            logger.warning("Bearer token is expired or about to expire. It will be refreshed on next login.")

        logger.info(f"Apple Music login successful. Account type: {account_type}, Storefront: {storefront}")

        account_pool.append({
            "uuid": account['uuid'],
            "username": media_user_token[:20] + "...",  # Truncate for privacy
            "service": "apple_music",
            "status": "active",
            "account_type": account_type,
            "bitrate": "256k",
            "login": {
                "session": session,
                "bearer_token": token,  # Store for expiry checking
                "token_fetched_at": time.time()  # Track when token was fetched
            }
        })
        return True

    except requests.exceptions.Timeout:
        error_msg = "Connection timeout - Apple Music servers may be slow or unreachable"
        logger.error(error_msg)
    except requests.exceptions.ConnectionError:
        error_msg = "Connection error - check your internet connection"
        logger.error(error_msg)
    except ValueError as e:
        error_msg = str(e)
        logger.error(f"Validation error: {error_msg}")
    except Exception as e:
        error_msg = f"Unknown error: {str(e)}"
        logger.error(error_msg)

    # Login failed - add error account
    account_pool.append({
        "uuid": account['uuid'],
        "username": account['login']['media-user-token'][:20] + "..." if account['login']['media-user-token'] else "N/A",
        "service": "apple_music",
        "status": "error",
        "account_type": "N/A",
        "bitrate": "N/A",
        "login": {
            "session": ""
        }
    })
    return False


def apple_music_get_token(parsing_index):
    return account_pool[parsing_index]['login']['session']


def apple_music_get_search_results(session, search_term, content_types):
    """Search Apple Music and return normalized results for the UI.

    This function is intentionally defensive around artwork handling because
    Apple may return items without artwork or with a null artwork URL.
    In those cases we simply omit the thumbnail instead of raising.
    """
    def _apple_music_artwork_url(entity, size: str = "160"):
        """Safely extract and format an artwork URL from an Apple entity.

        Returns None if artwork or url is missing so callers can treat the
        thumbnail as optional.
        """
        attributes = entity.get("attributes", {})
        artwork = attributes.get("artwork", {})
        url = artwork.get("url")

        if isinstance(url, str):
            return url.replace("{w}", size).replace("{h}", size)
        return None

    search_types = []
    if 'track' in content_types:
        search_types.append('songs')
    if 'album' in content_types:
        search_types.append('albums')
    if 'artist' in content_types:
        search_types.append('artists')
    if 'playlist' in content_types:
        search_types.append('playlists')

    params = {}
    params['term'] = search_term
    params['limit'] = config.get("max_search_results")
    params['types'] = ",".join(search_types)

    results = make_call(
        f'{BASE_URL}/catalog/{session.cookies.get("itua")}/search',
        params=params,
        session=session,
        skip_cache=True,
    )

    search_results = []

    try:
        results_dict = results.get('results', {}) if isinstance(results, dict) else {}

        for result in results_dict:

            if result == 'songs':
                for track in results_dict.get('songs', {}).get('data', []):
                    search_results.append({
                        'item_id': track['id'],
                        'item_name': track['attributes']['name'],
                        'item_by': track['attributes']['artistName'],
                        'item_type': "track",
                        'item_service': "apple_music",
                        'item_url': track['attributes']['url'],
                        'item_thumbnail_url': _apple_music_artwork_url(track),
                    })

            if result == 'albums':
                for album in results_dict.get('albums', {}).get('data', []):
                    search_results.append({
                        'item_id': album['id'],
                        'item_name': album['attributes']['name'],
                        'item_by': album['attributes']['artistName'],
                        'item_type': "album",
                        'item_service': "apple_music",
                        'item_url': album['attributes']['url'],
                        'item_thumbnail_url': _apple_music_artwork_url(album),
                    })

            if result == 'artists':
                for artist in results_dict.get('artists', {}).get('data', []):
                    search_results.append({
                        'item_id': artist['id'],
                        'item_name': artist['attributes']['name'],
                        'item_by': artist['attributes']['name'],
                        'item_type': "artist",
                        'item_service': "apple_music",
                        'item_url': artist['attributes']['url'],
                        'item_thumbnail_url': _apple_music_artwork_url(artist),
                    })

            if result == 'playlists':
                for playlist in results_dict.get('playlists', {}).get('data', []):
                    search_results.append({
                        'item_id': playlist['id'],
                        'item_name': playlist['attributes']['name'],
                        'item_by': playlist['attributes'].get('curatorName'),
                        'item_type': "playlist",
                        'item_service': "apple_music",
                        'item_url': playlist['attributes']['url'],
                        'item_thumbnail_url': _apple_music_artwork_url(playlist),
                    })

    except Exception as e:
        # Be resilient to unexpected Apple API changes; log and return
        # whatever results we successfully parsed instead of crashing the UI.
        logger.error(f"Error parsing Apple Music search results: {e}", exc_info=True)

    return search_results


def apple_music_get_track_metadata(session, item_id):
    logger.debug(f"Fetching metadata for track: {item_id}")
    params = {}
    params['include'] = 'lyrics'
    track_data = make_call(f'{BASE_URL}/catalog/{session.cookies.get("itua")}/songs/{item_id}', params=params, session=session)

    # Validate track data
    if not track_data.get('data'):
        raise ValueError(f"No data returned for track {item_id}. Track may not exist or be unavailable in your region.")

    album_data = None
    try:
        album_id = track_data.get('data', [])[0].get('relationships', {}).get('albums', {}).get('data', [])[0].get('id', {})
        album_data = make_call(f'{BASE_URL}/catalog/{session.cookies.get("itua")}/albums/{album_id}', session=session)
    except (IndexError, KeyError, TypeError) as e:
        logger.warning(f"Could not fetch album data for track {item_id}: {e}")
        album_data = None
    except Exception as e:
        logger.warning(f"Unexpected error fetching album data for track {item_id}: {e}")
        album_data = None

    # Artists
    artists = []
    artist_name = track_data.get('data', [])[0].get('attributes', {}).get('artistName', '')
    if artist_name:
        for artist in artist_name.replace("&", ",").split(","):
            artists.append(artist.strip())

    info = {}
    info['item_id'] = track_data.get('data', [])[0].get('id')
    info['album_name'] = track_data.get('data', [])[0].get('attributes', {}).get('albumName')
    info['genre'] = conv_list_format(track_data.get('data', [])[0].get('attributes', {}).get('genreNames', []))

    # Release year extraction with logging
    try:
        release_date = track_data.get('data', [])[0].get('attributes', {}).get('releaseDate')
        if release_date:
            info['release_year'] = release_date.split('-')[0]
    except (AttributeError, IndexError) as e:
        logger.debug(f"Could not extract release year for track {item_id}: {e}")
    info['length'] = str(track_data.get('data', [])[0].get('attributes', {}).get('durationInMillis'))
    info['isrc'] = track_data.get('data', [])[0].get('attributes', {}).get('isrc')

    image_url = track_data.get('data', [])[0].get('attributes', {}).get('artwork', {}).get('url')
    max_height = track_data.get('data', [])[0].get('attributes', {}).get('artwork', {}).get('height')
    max_width = track_data.get('data', [])[0].get('attributes', {}).get('artwork', {}).get('width')
    info['image_url'] = image_url.replace("{w}", str(max_width)).replace("{h}", str(max_height))

    info['writer'] = track_data.get('data', [])[0].get('attributes', {}).get('composerName')
    info['language'] = track_data.get('data', [])[0].get('attributes', {}).get('audioLocale')
    info['item_url'] = track_data.get('data', [])[0].get('attributes', {}).get('url')
    info['is_playable'] = True if track_data.get('data', [])[0].get('attributes', {}).get('playParams') else False
    info['disc_number'] = track_data.get('data', [])[0].get('attributes', {}).get('discNumber')
    info['title'] = track_data.get('data', [])[0].get('attributes', {}).get('name')
    info['explicit'] = True if track_data.get('data', [])[0].get('attributes', {}).get('contentRating') == 'explicit' else False
    info['artists'] = conv_list_format(artists)

    info['album_artists'] = artists[0]

    if album_data:
        info['copyright'] = album_data.get('data', [])[0].get('attributes', {}).get('copyright')
        info['upc'] = album_data.get('data', [])[0].get('attributes', {}).get('upc')
        info['label'] = album_data.get('data', [])[0].get('attributes', {}).get('recordLabel')
        info['total_tracks'] = album_data.get('data', [])[0].get('attributes', {}).get('trackCount')

        album_type = 'album'
        if album_data.get('data', [])[0].get('attributes', {}).get('isSingle'):
            album_type = 'single'
        if album_data.get('data', [])[0].get('attributes', {}).get('isCompilation'):
            album_type = 'compilation'
        info['album_type'] = album_type

        # Track Number
        track_number = None

        for i, track in enumerate(album_data.get('data', [])[0].get('relationships', {}).get('tracks', {}).get('data', [])):
            if track.get('id') == str(item_id):
                track_number = i + 1
                break
        if not track_number:
            track_number = track_data.get('data', [])[0].get('attributes', {}).get('trackNumber')

        # Total Discs
        total_discs = album_data.get('data', [])[0].get('relationships', {}).get('tracks', {}).get('data', [])[-1].get('attributes', {}).get('discNumber')

        info['track_number'] = track_number
        info['total_discs'] = total_discs

    return info


def apple_music_get_lyrics(session, item_id, item_type, metadata, filepath):
    params = {}
    params['include'] = 'lyrics'
    track_data = make_call(f'{BASE_URL}/catalog/{session.cookies.get("itua")}/songs/{item_id}', params=params, session=session)

    time_synced = track_data.get('data', [])[0].get('attributes', {}).get('hasTimeSyncedLyrics')
    if config.get('only_download_synced_lyrics') and not time_synced:
        return False

    if len(track_data.get('data', [])[0].get('relationships', {}).get('lyrics', {}).get('data', [])):
        ttml_data = track_data.get('data', [])[0].get('relationships', {}).get('lyrics', {}).get('data', [])[0].get('attributes', {}).get('ttml')
        lyrics_list = []

        if not config.get('only_download_plain_lyrics'):
            if config.get("embed_branding"):
                lyrics_list.append('[re:OnTheSpot]')

            for key in metadata.keys():
                value = metadata[key]
                if key in ['title', 'track_title', 'tracktitle'] and config.get("embed_name"):
                    lyrics_list.append(f'[ti:{value}]')
                elif key == 'artists' and config.get("embed_artist"):
                    lyrics_list.append(f'[ar:{value}]')
                elif key in ['album_name', 'album'] and config.get("embed_album"):
                    lyrics_list.append(f'[al:{value}]')
                elif key in ['writers'] and config.get("embed_writers"):
                    lyrics_list.append(f'[au:{value}]')

            if config.get("embed_length"):
                l_ms = int(metadata['length'])
                if round((l_ms/1000)/60) < 10:
                    digit="0"
                else:
                    digit=""
                lyrics_list.append(f'[length:{digit}{str((l_ms/1000)/60)[:1]}:{round((l_ms/1000)%60)}]\n')

        default_length = len(lyrics_list)

        for p in ET.fromstring(ttml_data.replace('`', '')).findall('.//{http://www.w3.org/ns/ttml}p'):
            begin_time = p.attrib.get('begin')
            lyric = p.text
            if lyric:
                if time_synced:
                    if ':' in begin_time:
                        time_parts = begin_time.split(':')
                        if len(time_parts) == 3:  # Format: HH:MM:SS.mmm
                            hours, minutes, seconds = time_parts
                            minutes = int(minutes) + (int(hours) * 60)
                        elif len(time_parts) == 2:  # Format: MM:SS.mmm
                            minutes, seconds = time_parts
                    else: # Format: SS.mmm
                        minutes = '0'
                        seconds = begin_time
                    try:
                        seconds, milliseconds = seconds.split('.')
                    except (TypeError, ValueError):
                        milliseconds = '0'
                    formatted_time = f"{int(minutes):02}:{int(seconds):02}.{milliseconds.replace('s', '')[:2]}"
                    if not config.get('only_download_plain_lyrics'):
                        lyric = f'[{formatted_time}] {lyric}'

                lyrics_list.append(lyric)

        merged_lyrics = '\n'.join(lyrics_list)
        if len(merged_lyrics) <= default_length:
            return False

        if config.get('save_lrc_file'):
            with open(filepath + '.lrc', 'w', encoding='utf-8') as f:
                f.write(merged_lyrics)
        if config.get('embed_lyrics'):
            return {"lyrics": merged_lyrics}
        else:
            return False


def apple_music_get_webplayback_info(session, item_id):
    """Get webplayback info for a track, including stream URLs."""
    logger.debug(f"Getting webplayback info for track: {item_id}")

    payload = {'salableAdamId': item_id}

    try:
        response = session.post(
            'https://play.itunes.apple.com/WebObjects/MZPlay.woa/wa/webPlayback',
            json=payload,
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        webplayback_info = response.json()
    except requests.exceptions.Timeout:
        raise Exception(f"Timeout getting playback info for track {item_id}")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise Exception("Authentication failed - your media-user-token may have expired")
        elif e.response.status_code == 403:
            raise Exception(f"Access denied for track {item_id} - may require subscription")
        raise Exception(f"HTTP error getting playback info: {e}")

    song_list = webplayback_info.get("songList")
    if not song_list:
        # Check for error messages
        failure_type = webplayback_info.get("failureType", "")
        if "SUBSCRIPTION" in failure_type.upper():
            raise Exception(f"Subscription required to play track {item_id}")
        elif "GEOGRAPHIC" in failure_type.upper() or "STOREFRONT" in failure_type.upper():
            raise Exception(f"Track {item_id} is not available in your region")
        elif failure_type:
            raise Exception(f"Playback failed for track {item_id}: {failure_type}")
        else:
            raise Exception(f"No playback info returned for track {item_id}")

    return song_list[0]


def apple_music_get_decryption_key(session, stream_url, item_id):
    """Extract DRM decryption key using Widevine CDM."""
    logger.debug(f"Getting decryption key for track: {item_id}")

    # Load m3u8 playlist
    try:
        m3u8_obj = m3u8.load(stream_url, verify_ssl=False)
    except Exception as e:
        raise Exception(f"Failed to load m3u8 playlist for track {item_id}: {e}")

    # Extract PSSH (Protection System Specific Header)
    if not m3u8_obj.keys:
        raise Exception(f"No encryption keys found in stream for track {item_id}. Track may be unencrypted or unavailable.")

    pssh = m3u8_obj.keys[0].uri
    if not pssh:
        raise Exception(f"PSSH data is empty for track {item_id}")

    logger.debug(f"Found PSSH data for track {item_id}")

    cdm_session = None
    try:
        # Parse PSSH and create Widevine challenge
        widevine_pssh_data = WidevinePsshData()
        widevine_pssh_data.algorithm = 1

        try:
            pssh_data = pssh.split(",")[1]
            widevine_pssh_data.key_ids.append(base64.b64decode(pssh_data))
        except (IndexError, ValueError) as e:
            raise Exception(f"Invalid PSSH format for track {item_id}: {e}")

        pssh_obj = PSSH(widevine_pssh_data.SerializeToString())
        cdm = Cdm.from_device(Device.loads(WVN_KEY))

        cdm_session = cdm.open()
        challenge = base64.b64encode(
            cdm.get_license_challenge(cdm_session, pssh_obj)
        ).decode()

        # Request license from Apple
        license_payload = {
            'challenge': challenge,
            'key-system': 'com.widevine.alpha',
            'uri': pssh,
            'adamId': item_id,
            'isLibrary': False,
            'user-initiated': True
        }

        logger.debug(f"Requesting license for track {item_id}")

        try:
            license_response = session.post(WVN_LICENSE_URL, json=license_payload, timeout=DEFAULT_TIMEOUT)
            license_response.raise_for_status()
            license_data = license_response.json()
        except requests.exceptions.Timeout:
            raise Exception(f"Timeout requesting license for track {item_id}")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise Exception("License request failed - authentication expired")
            elif e.response.status_code == 403:
                raise Exception(f"License denied for track {item_id} - subscription may be required")
            raise Exception(f"License request failed: {e}")

        # Check for errors in license response
        if 'error' in license_data:
            error_msg = license_data.get('error', {}).get('message', 'Unknown error')
            raise Exception(f"License server error for track {item_id}: {error_msg}")

        wvn_license = license_data.get('license')
        if not wvn_license:
            raise Exception(f"No license returned for track {item_id} - check subscription status")

        # Parse license and extract decryption key
        cdm.parse_license(cdm_session, wvn_license)

        content_keys = [key for key in cdm.get_keys(cdm_session) if key.type == "CONTENT"]
        if not content_keys:
            raise Exception(f"No content key found in license for track {item_id}")

        decryption_key = content_keys[0].key.hex()
        logger.debug(f"Successfully obtained decryption key for track {item_id}")

        return decryption_key

    finally:
        if cdm_session:
            cdm.close(cdm_session)


def apple_music_get_album_track_ids(session, album_id):
    logger.info(f"Getting tracks from album: {album_id}")
    album_data = make_call(f'{BASE_URL}/catalog/{session.cookies.get("itua")}/albums/{album_id}', session=session)
    item_ids = []
    for track in album_data.get('data', [])[0].get('relationships', {}).get('tracks', {}).get('data', []):
        if track['type'] == 'songs':
            item_ids.append(track['id'])
    return item_ids


def apple_music_get_artist_album_ids(session, artist_id):
    logger.info(f"Getting album ids for artist: '{artist_id}'")

    params = {}
    params['include'] = 'albums'
    params['views'] = 'full-albums,singles,live-albums'

    album_data = make_call(f'{BASE_URL}/catalog/{session.cookies.get("itua")}/artists/{artist_id}', params=params, session=session)

    item_ids = []
    for album in album_data.get('data', [])[0].get('relationships', {}).get('albums', {}).get('data', []):
        item_ids.append(album.get('id'))
    return item_ids


def apple_music_get_playlist_data(session, playlist_id):
    logger.info(f"Get playlist data for playlist: {playlist_id}")
    playlist_data = make_call(f"{BASE_URL}/catalog/{session.cookies.get('itua')}/playlists/{playlist_id}", session=session, skip_cache=True)
    playlist_name = playlist_data.get('data', [])[0].get('attributes', {}).get('name')
    playlist_by =  playlist_data.get('data', [])[0].get('attributes', {}).get('curatorName')

    track_ids = []
    offset = 0
    while True:
        url = f'{BASE_URL}/catalog/{session.cookies.get("itua")}/playlists/{playlist_id}/tracks?offset={offset}'
        playlist_track_data = make_call(url, session=session, skip_cache=True)
        for track in playlist_track_data.get('data'):
            track_ids.append(track.get('id'))
        if 'next' in playlist_track_data:
            offset += 100
        else:
            break

    return playlist_name, playlist_by, track_ids
