import os
from .accounts import get_account_token
from .api.apple_music import apple_music_get_search_results
from .api.bandcamp import bandcamp_get_search_results
from .api.deezer import deezer_get_search_results
from .api.qobuz import qobuz_get_search_results
from .api.soundcloud import soundcloud_get_search_results
from .api.spotify import spotify_get_search_results
from .api.tidal import tidal_get_search_results
from .api.youtube_music import youtube_music_get_search_results
from .api.crunchyroll import crunchyroll_get_search_results
from .otsconfig import config
from .parse_item import parse_url
from .runtimedata import account_pool, get_logger

logger = get_logger("search")


def get_search_results(search_term, content_types=None):
    if len(account_pool) <= 0:
        return None

    if search_term == '':
        logger.warning(f"Returning empty data as query is empty !")
        return False

    # Support multiple URLs entered in a single-line box where newlines can
    # be stripped out. We look for multiple occurrences of "https://" and
    # split the string on that marker so that even
    # "https://url1https://url2" is handled.
    if search_term.count("https://") > 1:
        parts = search_term.split("https://")
        multi_urls = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            multi_urls.append("https://" + part)

        if len(multi_urls) > 1:
            for idx, url in enumerate(multi_urls, start=1):
                logger.info(f"[{idx}] Parsing URL from multi-URL search input: {url}")
                result = parse_url(url)
                if result is False:
                    logger.warning(f"[{idx}] Invalid URL in multi-URL search input: {url}")
            # All URLs have been handed off to the parsing worker; there are no
            # search-table results to display in this mode.
            return True

    # Single-URL mode (original behaviour) still supports both https and http.
    if search_term.startswith('https://') or search_term.startswith('http://'):
        logger.info(f"Search clicked with value with url {search_term}")
        result = parse_url(search_term)
        if result is False:
            return False
        return True
    else:
        # If the search term is a path to a file, parse each https:// URL in it.
        if os.path.isfile(search_term):
            with open(search_term, 'r', encoding='utf-8') as sf:
                links = sf.readlines()
                for idx, link in enumerate(links, start=1):
                    link = link.strip()
                    if link.startswith("https://"):
                        logger.debug(f'[{idx}] Parsing link from {search_term}: {link}')
                        parse_url(link)
            return True

        logger.info(f"Search clicked with value term {search_term}")
        service = account_pool[config.get('active_account_number')]['service']
        if search_term and service != 'generic':
            token = get_account_token(service)
            return globals()[f"{service}_get_search_results"](token, search_term, content_types)
        else:
            return False
