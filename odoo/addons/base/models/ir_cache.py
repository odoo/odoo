import hashlib
import hmac as hmac_lib
import json
import logging
import re
import shutil
from collections.abc import Sequence, Buffer
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from pathlib import Path

from odoo import api, fields, models, release
from odoo.tools import SQL, config
from odoo.tools.misc import hkdf_expand
from odoo.tools.sql import escape_like_value

_logger = logging.getLogger(__name__)


def _get_ir_cache_secret(env: api.Environment) -> bytes:
    """ Return the HMAC key signing the entries of the database, derived
    from the config ``config.server_secret``. The key never leaves the process: it is
    neither stored, nor sent to the database, nor logged.
    """
    db_secret = env['ir.config_parameter'].sudo().get_str('database.secret')
    # A key per database: a valid entry can not be replayed in another
    # database. Its secret rather than its name: the cache survives a renaming,
    # and a duplicated database gets a new secret. A key per version of Odoo:
    # the data derived from the database depends on its code. Not per version
    # of python: only some kinds depend on it (e.g. marshalled code objects),
    # they put it in their keys, see `ir.qweb._get_cache_key`.
    info = f'odoo ir.cache {db_secret} {release.version}'.encode()
    return hkdf_expand(hashlib.sha256, config.server_secret, info, 32)


class IrCachePending:
    """ The entries waiting for the commit of a read-only cursor. ``rows__``
    is out of reach of `safe_eval` (server actions, QWeb expressions). """
    def __init__(self):
        self.rows__ = []


_KIND_RE = re.compile(r'\w+')


def _get_ir_cache_filename(kind: str, create_date: datetime, signature: bytes) -> str:
    """ Return the name of the file of the value of an entry: its signature
    identifies the value, two entries with the same file have the same value. """
    if not _KIND_RE.fullmatch(kind):
        raise ValueError(f"Invalid ir.cache kind {kind!r}")
    return f"{kind}-{create_date.strftime('%Y%m%d%H%M%S%f')}-{signature.hex()}"


class IrCache(models.Model):
    """ Persistent cache of data derived from the database, like the compiled
    code of the QWeb templates, shared by the workers and the restarts.

    The values are bytes, that the caller may load as executable code (e.g.
    the QWeb code objects stored with :mod:`marshal`), and anybody may write
    in the table (ORM, server action, SQL injection, psql...) or in the
    files of the values (next to the filestore, see
    :meth:`~odoo.tools.config.configmanager.cache_dir`): an entry is used
    only if its file exists and its signature is valid, see :meth:`_lookup_multi`.
    The signature is computed with a key that only lives in the memory of
    the server (see :func:`_get_ir_cache_secret`), so a valid entry can only
    be produced by :meth:`_set__`.

    The entries are never updated nor invalidated: a new entry is added for
    the same ``(kind, key)`` and the last one is used if it still matches
    its source: its ``version`` is computed from its ``version_data`` by an SQL
    query given by the caller (specific to the ``kind``), when the entry is
    created and when it is read, or given as a constant string. The query
    computes the versions of all the entries at once. Or the caller deletes
    its entries when their source changes, see :meth:`_clear` (e.g.
    ``ir.qweb._clear_cache``).

    The entries do not depend on the version of python: a kind whose values
    do (e.g. code objects stored with :mod:`marshal`, loading those of
    another version may crash the interpreter) must put
    ``importlib.util.MAGIC_NUMBER`` in its keys, see ``ir.qweb._get_cache_key``.

    When the key of the signatures changes (server secret, database secret,
    version of Odoo), all the entries are deleted at once by the cron
    triggered at the start of the server (until then, they are rejected one
    by one),
    see :meth:`_check_secret` and :meth:`_gc_cache`.

    The entries and the files older than ``_cache_max_hours`` are deleted by
    :meth:`_gc_cache` (daily cron): the code producing them (e.g. the QWeb
    compiler) may be fixed without changing the version of Odoo, a fix
    applies to the cached data after that delay plus one day at most.
    """
    _name = 'ir.cache'
    _description = 'Persistent cache'
    _log_access = False
    _allow_sudo_commands = False

    _cache_max_hours = 7 * 24

    create_date = fields.Datetime(string="Create Date", readonly=True)
    kind = fields.Char(string="Type of the entry", required=True, help="Type of the entry, e.g. 'qweb'")
    key = fields.Char(string="Cache Key", required=True, help="Cache Key, e.g. 'website.layout'")
    version_data = fields.Json(string="Version Data", required=True, help="Data identifying the source of the entry used by the SQL to check the version, e.g. view ids")
    version = fields.Char(string="Version", required=True, help="Version of the source (hash computed from the version_data) when the entry was created")
    signature = fields.Binary(attachment=False, required=True)

    _kind_key_idx = models.UniqueIndex('(kind, key, id DESC)')

    @api.private
    def browse(self, ids=()):
        if not ids:
            return super().browse()
        raise RuntimeError("Cannot instantiate ir.cache")

    def _register_hook(self):
        """ Check the canary entry. When it is missing or signed with another
        key, trigger :meth:`_gc_cache`, which deletes all the entries.
        """
        super()._register_hook()

        if not self._check_secret():
            if self.env.execute_query(SQL("SELECT id FROM ir_cache WHERE kind = 'ir_cache'")):
                _logger.info("ir.cache: the key of the signatures changed")
            if cron := self.env.ref('base.ir_cron_ir_cache_gc', raise_if_not_found=False):
                # the cron does not exist yet if the code is deployed before the update of base
                cron._trigger()

    @api.model
    def _check_secret(self) -> bool:
        """ Check the canary entry, signed like the other entries.

        :return: whether the canary is valid, i.e. the entries are signed with
            the current key
        """
        return self._lookup('ir_cache', 'ir.cache') == b'0'

    @api.model
    def _lookup(self, kind: str, key: str, version: SQL | str = '') -> bytes | None:
        return self._lookup_multi(kind, [key], version=version)[0]

    @api.model
    def _lookup_multi(self, kind: str, keys: Sequence[str], version: SQL | str = '') -> Sequence[bytes | None]:
        """ Return the value of the last entry of each key, if its signature
        is valid and if its source did not change: its ``version`` is equal to
        ``version``, or to the one computed by the query ``version`` from its
        ``version_data``.
        Nothing else is trustworthy: an entry whose file is missing is a miss,
        an entry with an invalid signature is ignored, and the canary is
        checked (see :meth:`_check_secret`). The age of the entries is not
        checked,
        see :meth:`_gc_cache`.

        :param str kind: the type of the entries, e.g. ``'qweb'``
        :param keys: the keys of the entries
        :param version: either the SQL query computing the versions of the
            sources of the entries from their ``version_data``, or the
            version itself as a string (e.g. a version of the source); with the default, the entries stored
            without ``version`` are returned
        :return: the values (bytes) in the order of ``keys``, ``None`` for
            the keys without a valid entry
        """
        if not keys:
            return ()
        secret = _get_ir_cache_secret(self.env)

        if not isinstance(version, SQL):
            version = SQL("SELECT key, %s AS version FROM entry", version)

        rows = self.env.execute_query(SQL("""
            WITH
                entry AS MATERIALIZED (
                    SELECT DISTINCT ON (key) key, version_data, version, create_date, signature
                    FROM ir_cache
                    WHERE kind = %s AND key = ANY(%s)
                    ORDER BY key, id DESC
                ),
                -- computed once for all the entries, whatever the estimates
                source AS MATERIALIZED (%s)
            SELECT entry.key, entry.version_data, entry.version, entry.create_date, entry.signature
            FROM entry
            JOIN source ON source.key = entry.key
            WHERE entry.version = source.version
        """, kind, list(keys), version))

        # the entries added by this transaction with a read-only cursor (see
        # `_set__`): not more trustworthy than the table, check them like the
        # rows, the signature against forged values, the version recomputed
        # from the version_data against replayed old entries
        postcommit_data = self.env.cr.postcommit.data
        pending = postcommit_data['ir.cache.pending'].rows__ if 'ir.cache.pending' in postcommit_data else ()

        pending_sql = [
            SQL("(%s, %s::jsonb, %s, %s::timestamp, %s::bytea)", key, version_data, version_, create_date, signature)
            for (create_date, kind_, key, version_data, version_, signature) in pending
            if kind_ == kind and key in keys
        ]
        if pending_sql:
            rows.extend(self.env.execute_query(SQL("""
                WITH
                    entry (key, version_data, version, create_date, signature) as (SELECT * FROM (VALUES %s)),
                    source AS MATERIALIZED (%s)
                SELECT entry.key, entry.version_data, entry.version, entry.create_date, entry.signature
                FROM entry
                JOIN source ON source.key = entry.key
                WHERE entry.version = source.version
            """, SQL(", ").join(pending_sql), version)))

        directory = Path(config.cache_dir(self.env.cr.dbname))
        result = {}
        invalid = []
        for key, version_data, version_, create_date, signature in rows:
            signature = bytes(signature)
            try:
                data = (directory / _get_ir_cache_filename(kind, create_date, signature)).read_bytes()
            except OSError:
                continue  # e.g. deleted by the GC, or another server without the cache
            message = b'\0'.join([kind.encode(), key.encode(), json.dumps(version_data, sort_keys=True).encode(), version_.encode(), data])  # canonical, jsonb does not keep the formatting
            if not hmac_lib.compare_digest(signature, hmac_lib.digest(secret, message, 'sha256')):
                invalid.append(key)
            else:
                result[key] = data
        if invalid and kind != 'ir_cache' and self._check_secret():
            _logger.info("ir.cache: invalid signature of the %s entries %r, ignored", kind, invalid)
        return tuple(result.get(key) for key in keys)

    @api.model
    def _set__(self, kind: str, key: str, value: Buffer, version_data: list | tuple | dict | None = None, version: SQL | str = ''):
        """ Add a signed entry for ``value``, with ``version``, or the version
        computed by the query ``version`` from ``version_data``. The value is
        written in a file, the entry is added only if the file is written.
        This must be done in the transaction that produced ``value``: when the
        transaction is rolled back, the entry is either rolled back too, or
        does not match its source anymore. With a read-only cursor, the entry is
        stored by a new cursor after the commit, and :meth:`_lookup_multi` returns it
        until then.

        :param str kind: the type of the entry, e.g. ``'qweb'``
        :param str key: the key of the entry
        :param value: the bytes to store, e.g. code objects dumped with
            ``marshal``
        :param version_data: the data identifying the source of the entry, any
            value supported by ``json``, e.g. view ids; the query ``version``
            computes the version from it, so it requires ``version`` as ``SQL``
        :param version: either the SQL query computing the version of the source
            of the entry from ``version_data``, or the version itself as a
            string; with the default, the entry is stored
            with an empty version, invalidated by :meth:`_clear` only
        """
        secret = _get_ir_cache_secret(self.env)

        version_data_json = json.dumps(version_data, sort_keys=True)

        if isinstance(version, SQL):
            [[version_value]] = self.env.execute_query(SQL("""
                WITH entry AS MATERIALIZED (SELECT %s::varchar AS key, %s::jsonb AS version_data)
                SELECT source.version FROM (%s) source
            """, key, version_data_json, version))
        elif bool(version_data):
            raise ValueError("A control needs a hash which is a SQL")
        else:
            version_value = version
            version = SQL("SELECT key, %s AS version FROM entry", version)

        data = bytes(value)
        message = b'\0'.join([kind.encode(), key.encode(), version_data_json.encode(), version_value.encode(), data])  # same as in `_lookup_multi`

        signature = hmac_lib.digest(secret, message, 'sha256')
        create_date = datetime.now(timezone.utc).replace(tzinfo=None)

        # The name of the file is unique, and its entry is visible only after
        # the commit: nobody reads the file while it is written. If the
        # transaction is rolled back, the file expires like the others.
        directory = Path(config.cache_dir(self.env.cr.dbname))
        try:
            directory.mkdir(parents=True, exist_ok=True)
            (directory / _get_ir_cache_filename(kind, create_date, signature)).write_bytes(data)
        except OSError as e:
            _logger.info("ir.cache: failed to write the %s entry %r: %s", kind, key, e)
            return

        row = (create_date, kind, key, version_data_json, version_value, signature)

        if kind == 'ir_cache':
            _logger.info("ir.cache: new canary created")

        if not self.env.cr.readonly:
            self.env.cr.execute(
                SQL("""
                INSERT INTO ir_cache (create_date, kind, key, version_data, version, signature)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, *row)
            )
            return

        # A read-only cursor can not write: insert the entries with a new
        # cursor after the commit, `_lookup_multi` reads them in the meantime. The version
        # is the one of the source seen by the transaction that produced the
        # value: if the source changed in the meantime, the entry is simply
        # not used.
        # in the data of the postcommit: cleared with it on commit and rollback
        rows = self.env.cr.postcommit.data.setdefault('ir.cache.pending', IrCachePending()).rows__
        if not rows:
            registry = self.env.registry

            @self.env.cr.postcommit.add
            def insert_entries():
                try:
                    with registry.cursor() as cr:
                        cr.execute(SQL(
                            "INSERT INTO ir_cache (create_date, kind, key, version_data, version, signature) VALUES %s",
                            SQL(", ").join(SQL("(%s, %s, %s, %s, %s, %s)", *row) for row in rows),
                        ))
                except Exception as e:  # noqa: BLE001
                    # the response is already computed, the entries are only a cache
                    _logger.info("ir.cache: failed to store %s entries: %s", len(rows), e)

        rows.append(row)

    @api.model
    def _clear(self, kind: str, prefixes: Sequence[str] | None = None):
        """ Delete the entries of ``kind`` whose key starts with one of
        ``prefixes``, or all the entries of ``kind``. Their files expire like
        the others, see :meth:`_gc_cache`.

        :param str kind: the type of the entries, e.g. ``'qweb'``
        :param prefixes: the beginnings of the keys of the entries to delete
        """
        if prefixes:
            patterns = [f"{escape_like_value(prefix)}%" for prefix in prefixes or ['']]
            self.env.cr.execute(SQL(
                "DELETE FROM ir_cache WHERE kind = %s AND key LIKE ANY(%s)",
                kind, patterns,
            ))
        else:
            self.env.cr.execute(SQL(
                "DELETE FROM ir_cache WHERE kind = %s",
                kind,
            ))
        _logger.info("ir.cache: %s entries deleted", self.env.cr.rowcount)

    @api.model
    def _gc_cache(self):
        """ Called by the cron ``base.ir_cron_ir_cache_gc``, daily and when
        :meth:`_register_hook` finds an invalid canary. When the canary is
        missing or signed with another key, delete all the entries (they may
        be signed with that key too) and their files, and add a new canary.
        Otherwise delete the entries older than ``_cache_max_hours``, except
        the canary.
        """
        directory = Path(config.cache_dir(self.env.cr.dbname))
        if not self._check_secret():
            self.env.cr.execute("TRUNCATE ir_cache")
            shutil.rmtree(directory, ignore_errors=True)
            _logger.info("ir.cache: all entries deleted")
            self._set__('ir_cache', 'ir.cache', b'0')
            return

        self.env.cr.execute(SQL("""
            DELETE FROM ir_cache c
              WHERE c.create_date < NOW() AT TIME ZONE 'UTC' - make_interval(hours => %s)
                AND kind != 'ir_cache'
        """, self._cache_max_hours))
        _logger.info("ir.cache: %s entries deleted", self.env.cr.rowcount)

        limit_time = datetime.now(timezone.utc).replace(tzinfo=None) - relativedelta(hours=self._cache_max_hours)
        time_str = limit_time.strftime('%Y%m%d%H%M%S%f')

        count = 0
        for path in directory.iterdir():
            try:
                parts = path.name.rsplit('-', 2)
                if len(parts) == 3 and parts[1] < time_str and parts[0] != 'ir_cache':
                    path.unlink()
                    count += 1
            except OSError:
                pass  # deleted by another GC
        _logger.info("ir.cache: %s files deleted", count)
