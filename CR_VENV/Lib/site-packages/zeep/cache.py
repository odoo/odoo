import base64
import datetime
import errno
import logging
import os
import threading
import typing
from contextlib import contextmanager

import platformdirs
import pytz

# The sqlite3 is not available on Google App Engine so we handle the
# ImportError here and set the sqlite3 var to None.
# See https://github.com/mvantellingen/python-zeep/issues/243
try:
    import sqlite3
except ImportError:
    sqlite3 = None  # type: ignore

logger = logging.getLogger(__name__)


class Base:
    """Base class for caching backends."""

    def add(self, url, content):
        raise NotImplementedError()

    def get(self, url):
        raise NotImplementedError()


class VersionedCacheBase(Base):
    """Versioned base class for caching backends.
    Note when subclassing a version class attribute must be provided.
    """

    def _encode_data(self, data):
        """Helper function for encoding cacheable content as base64.
        :param data: Content to be encoded.
        :rtype: bytes
        """
        data = base64.b64encode(data)
        return self._version_string + data

    def _decode_data(self, data):
        """Helper function for decoding base64 cached content.
        :param data: Content to be decoded.
        :rtype: bytes
        """
        if data.startswith(self._version_string):
            return base64.b64decode(data[len(self._version_string) :])

    @property
    def _version_string(self):
        """Expose the version prefix to be used in content serialization.
        :rtype: bytes
        """
        assert (
            getattr(self, "_version", None) is not None
        ), "A version must be provided in order to use the VersionedCacheBase backend."
        prefix = u"$ZEEP:%s$" % self._version
        return bytes(prefix.encode("ascii"))


class InMemoryCache(Base):
    """Simple in-memory caching using dict lookup with support for timeouts"""

    #: global cache, thread-safe by default
    _cache = (
        {}
    )  # type: typing.Dict[str, typing.Tuple[datetime.datetime, typing.Union[bytes, str]]]

    def __init__(self, timeout=3600):
        self._timeout = timeout

    def add(self, url, content):
        logger.debug("Caching contents of %s", url)
        if not isinstance(content, (str, bytes)):
            raise TypeError(
                "a bytes-like object is required, not {}".format(type(content).__name__)
            )
        self._cache[url] = (datetime.datetime.utcnow(), content)

    def get(self, url):
        try:
            created, content = self._cache[url]
        except KeyError:
            pass
        else:
            if not _is_expired(created, self._timeout):
                logger.debug("Cache HIT for %s", url)
                return content
        logger.debug("Cache MISS for %s", url)
        return None


class SqliteCache(VersionedCacheBase):
    """Cache contents via a sqlite database on the filesystem."""

    _version = "1"

    def __init__(self, path=None, timeout=3600):

        if sqlite3 is None:
            raise RuntimeError("sqlite3 module is required for the SqliteCache")

        # No way we can support this when we want to achieve thread safety
        if path == ":memory:":
            raise ValueError(
                "The SqliteCache doesn't support :memory: since it is not "
                + "thread-safe. Please use zeep.cache.InMemoryCache()"
            )

        self._lock = threading.RLock()
        self._timeout = timeout
        self._db_path = path if path else _get_default_cache_path()

        # Initialize db
        with self.db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                    CREATE TABLE IF NOT EXISTS request
                    (created timestamp, url text, content text)
                """
            )
            conn.commit()

    @contextmanager
    def db_connection(self):
        with self._lock:
            connection = sqlite3.connect(
                self._db_path, detect_types=sqlite3.PARSE_DECLTYPES
            )
            yield connection
            connection.close()

    def add(self, url, content):
        logger.debug("Caching contents of %s", url)
        data = self._encode_data(content)

        with self.db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM request WHERE url = ?", (url,))
            cursor.execute(
                "INSERT INTO request (created, url, content) VALUES (?, ?, ?)",
                (datetime.datetime.utcnow(), url, data),
            )
            conn.commit()

    def get(self, url):
        with self.db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT created, content FROM request WHERE url=?", (url,))
            rows = cursor.fetchall()

        if rows:
            created, data = rows[0]
            if not _is_expired(created, self._timeout):
                logger.debug("Cache HIT for %s", url)
                return self._decode_data(data)
        logger.debug("Cache MISS for %s", url)


def _is_expired(value, timeout):
    """Return boolean if the value is expired"""
    if timeout is None:
        return False

    now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
    max_age = value.replace(tzinfo=pytz.utc)
    max_age += datetime.timedelta(seconds=timeout)
    return now > max_age


def _get_default_cache_path():
    path = platformdirs.user_cache_dir("zeep", False)
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
    return os.path.join(path, "cache.db")
