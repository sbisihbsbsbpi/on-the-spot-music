import linecache
import logging
import os
import sys
import time
import tracemalloc
from functools import wraps
from logging.handlers import RotatingFileHandler
from threading import RLock, Condition
from .otsconfig import config

log_formatter = logging.Formatter(
    '[%(asctime)s :: %(name)s :: %(pathname)s -> %(lineno)s:%(funcName)20s() :: %(levelname)s] -> %(message)s'
)
log_handler = RotatingFileHandler(config.get("_log_file"),
                                  mode='a',
                                  maxBytes=(5 * 1024 * 1024),
                                  backupCount=2,
                                  encoding='utf-8',
                                  delay=0)
stdout_handler = logging.StreamHandler(sys.stdout)
log_handler.setFormatter(log_formatter)
stdout_handler.setFormatter(log_formatter)

account_pool = []
temp_download_path = []
parsing = {}
pending = {}
download_queue = {}
parsing_lock = RLock()
pending_lock = RLock()
download_queue_lock = RLock()
parsing_condition = Condition(parsing_lock)
pending_condition = Condition(pending_lock)
download_queue_condition = Condition(download_queue_lock)


def pop_next_parsing_item(block=False, timeout=None):
    """Thread-safe helper to pop the next item from the parsing dict.

    When *block* is ``False`` (default), this behaves like the original
    implementation and returns immediately with ``(None, None)`` when the
    dict is empty.

    When *block* is ``True``, the call will wait until an item becomes
    available or until *timeout* seconds have elapsed (if provided), in
    which case ``(None, None)`` is returned.
    """
    with parsing_condition:
        if not parsing:
            if not block:
                return None, None

            deadline = None
            if timeout is not None:
                deadline = time.monotonic() + timeout

            while not parsing:
                if timeout is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return None, None
                    parsing_condition.wait(timeout=remaining)
                else:
                    parsing_condition.wait()

        item_id = next(iter(parsing))
        return item_id, parsing.pop(item_id)


def pop_next_pending_item(block=False, timeout=None):
    """Thread-safe helper to pop the next item from the pending dict.

    When *block* is ``False`` (default), this behaves like the original
    implementation and returns immediately with ``(None, None)`` when the
    dict is empty.

    When *block* is ``True``, the call will wait until an item becomes
    available or until *timeout* seconds have elapsed (if provided), in
    which case ``(None, None)`` is returned.
    """
    with pending_condition:
        if not pending:
            if not block:
                return None, None

            deadline = None
            if timeout is not None:
                deadline = time.monotonic() + timeout

            while not pending:
                if timeout is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return None, None
                    pending_condition.wait(timeout=remaining)
                else:
                    pending_condition.wait()

        local_id = next(iter(pending))
        return local_id, pending.pop(local_id)


def requeue_pending_item(local_id, item):
    """Safely put an item back into the pending dict and notify waiters."""
    with pending_condition:
        pending[local_id] = item
        pending_condition.notify()


def enqueue_parsing_item(item_id, item):
    """Safely add or replace an item in the ``parsing`` dict.

    This helper centralises writes so callers do not need to manipulate the
    shared dict directly, keeping locking consistent with
    :func:`pop_next_parsing_item` and waking any waiting parsing workers.
    """
    with parsing_condition:
        parsing[item_id] = item
        parsing_condition.notify()


def enqueue_pending_item(local_id, item):
    """Safely add or replace an item in the ``pending`` dict.

    Centralising writes through this helper makes it easier to evolve the
    pending queue implementation later without touching all producers, and
    ensures any waiting queue workers are notified when new work arrives.
    """
    with pending_condition:
        pending[local_id] = item
        pending_condition.notify()


def acquire_next_download_item(block=False, timeout=None):
    """Get the next available item from ``download_queue`` in a thread-safe way.

    When *block* is ``False`` (default), this behaves like the original
    implementation and returns immediately when there are no items or when no
    suitable item is currently available.

    When *block* is ``True``, the call will wait until the queue is non-empty
    or until *timeout* seconds have elapsed (if provided). Note that if there
    are items present but all are currently marked unavailable, this helper
    still returns ``None`` immediately, matching the previous behaviour.
    """
    with download_queue_condition:
        if not download_queue:
            if not block:
                return None

            deadline = None
            if timeout is not None:
                deadline = time.monotonic() + timeout

            while not download_queue:
                if timeout is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return None
                    download_queue_condition.wait(timeout=remaining)
                else:
                    download_queue_condition.wait()

        iterator = iter(download_queue)
        while True:
            try:
                local_id = next(iterator)
            except StopIteration:
                return None

            item = download_queue[local_id]
            if item.get('available') is False:
                continue

            item['available'] = False
            return item


def add_to_download_queue(local_id, item):
    """Insert or replace an item in ``download_queue`` in a thread-safe way.

    New or updated items will wake any download workers that are blocked
    waiting for work.
    """
    with download_queue_condition:
        download_queue[local_id] = item
        download_queue_condition.notify()


def get_queue_sizes():
    """Return a snapshot of the current queue sizes.

    The lengths are computed under the appropriate locks so they are safe
    to use from UIs or diagnostic code without racing concurrent workers.
    """
    with parsing_condition:
        parsing_len = len(parsing)
    with pending_condition:
        pending_len = len(pending)
    with download_queue_condition:
        download_len = len(download_queue)
    return {
        "parsing": parsing_len,
        "pending": pending_len,
        "download_queue": download_len,
    }


init_tray = False


def set_init_tray(value):
    global init_tray
    init_tray = value


def get_init_tray():
    return init_tray


loglevel = int(os.environ.get("LOG_LEVEL", 20))


def get_logger(name):
    logger = logging.getLogger(name)
    logger.addHandler(log_handler)
    logger.addHandler(stdout_handler)
    logger.setLevel(loglevel)
    return logger


logger_ = get_logger("runtimedata")


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger_.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception

def log_function_memory(wrap_func):
    tracemalloc.start()
    top_limit = 10
    def display_top(snapshot, snapshot_log_prefix, key_type='lineno'):
        snapshot = snapshot.filter_traces((
            tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
            tracemalloc.Filter(False, "<unknown>"),
        ))
        top_stats = snapshot.statistics(key_type)

        logger_.debug(f"{snapshot_log_prefix} Top {top_limit} lines")
        for index, stat in enumerate(top_stats[:top_limit], 1):
            frame = stat.traceback[0]
            logger_.debug("#%s: %s:%s: %.1f KiB"
                % (index, frame.filename, frame.lineno, stat.size / 1024))
            line = linecache.getline(frame.filename, frame.lineno).strip()
            if line:
                logger_.debug(f"{snapshot_log_prefix} -- {line}"  )

        other = top_stats[top_limit:]
        if other:
            size = sum(stat.size for stat in other)
            logger_.debug("%s other: %.1f KiB" % (len(other), size / 1024))
        total = sum(stat.size for stat in top_stats)
        logger_.debug("Total allocated size: %.1f KiB" % (total / 1024))

    @wraps(wrap_func)
    def snapshot_function_call(*args, **kwargs):
        prefix = f"{wrap_func.__name__}: "
        before_func = tracemalloc.take_snapshot()
        logger_.debug(f"Snapshotting before {wrap_func.__name__} call")
        ret_val = wrap_func(*args, **kwargs)
        display_top(before_func, prefix)
        logger_.debug(f"Snapshotting after {wrap_func.__name__} call")
        after_func = tracemalloc.take_snapshot()
        display_top(after_func, prefix)
        top_stats = after_func.compare_to(before_func, 'lineno')
        logger_.debug(f"{prefix} Top {top_limit} differences")
        for stat in top_stats[:10]:
            logger_.debug(f"{prefix}{stat}")
        return ret_val
    return snapshot_function_call
