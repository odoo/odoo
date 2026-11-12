import hashlib
import hmac as hmac_lib
import importlib.util
import json
import logging
import shutil
import sys
import time
from collections.abc import Collection, Buffer
from datetime import datetime, timezone
from pathlib import Path

from odoo import api, fields, models, release
from odoo.tools import SQL, config
from odoo.tools.misc import hkdf_expand

_logger = logging.getLogger(__name__)


def _get_ir_cache_secret(env: api.Environment) -> bytes:
    """ Return the HMAC key signing the entries of the database, derived
    from the config ``config.server_secret``. The key never leaves the process: it is
    neither stored, nor sent to the database, nor logged.
    """
    db_secret = env['ir.config_parameter'].sudo().get_str('database.secret')
    # A key per database: a valid entry can not be replayed in another
    # database. Its secret rather than its name: the cache survives a renaming,
    # and a duplicated database gets a new secret. A key per version of Odoo
    # and of python: the marshalled code objects are not portable, the
    # entries of another version are simply not read.
    info = f'odoo ir.cache {db_secret} {release.version} {sys.version} '.encode() + importlib.util.MAGIC_NUMBER
    return hkdf_expand(hashlib.sha256, config.server_secret, info, 32)


def _get_ir_cache_filename(kind: str, create_date: datetime, signature: bytes) -> str:
    """ Return the name of the file of the value of an entry: its signature
    identifies the value, two entries with the same file have the same value. """
    return f"{kind}-{create_date.strftime('%Y%m%d%H%M%S%f')}-{signature.hex()}"


class IrCache(models.Model):
    """ Persistent cache of data derived from the database, like the compiled
    code of the QWeb templates, shared by the workers and the restarts.

    The values are bytes, that the caller may load as executable code (e.g.
    the QWeb code objects stored with :mod:`marshal`), and anybody may write
    in the table (ORM, server action, SQL injection, psql...) or in the
    files of the values (next to the filestore, see
    :meth:`~odoo.tools.config.configmanager.cache_dir`): an entry is used
    only if its file exists and its signature is valid, see :meth:`_get`.
    The signature is computed with a key that only lives in the memory of
    the server (see :func:`_get_ir_cache_secret`), so a valid entry can only
    be produced by :meth:`_set__`.

    The entries are never updated nor invalidated: a new entry is added for
    the same ``(kind, key)`` and the last one is used if it still matches
    its source: its ``hash`` is computed from its ``control`` by an SQL
    expression given by the caller (specific to the ``kind``), when the
    entry is created and when it is read.

    When the key changes (config admin_passwd, database secret, version of
    Odoo or python), all the entries are deleted at once instead of being
    rejected one by one, see :meth:`_check_secret` and :meth:`_gc_cache`.

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
    control = fields.Json(string="Validation data identifying", required=True, help="Data identifying the source of the entry, e.g. view ids")
    hash = fields.Char(string="Validation Hash", required=True, help="Hash of the source (computed from the control) when the entry was created")
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
            if self.env.execute_query(SQL("SELECT id FROM ir_cache WHERE kind = 'ir.cache'")):
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
        data = self._get('ir.cache', ('ir.cache',))
        return data.get('ir.cache') == b'0'

    @api.model
    def _get(self, kind: str, keys: Collection[str], hash: SQL | str = '') -> dict[str, bytes]:
        """ Return the value of the last entry of each key, if its signature
        is valid and if its source did not change: its ``hash`` is equal to
        ``hash``, or to the expression ``hash`` computed from its ``control``.
        Nothing else is trustworthy: an entry whose file is missing is a miss,
        an entry with an invalid signature is ignored, and the canary is
        checked (see :meth:`_check_secret`). The age of the entries is not
        checked,
        see :meth:`_gc_cache`.

        :param str kind: the type of the entries, e.g. ``'qweb'``
        :param keys: the keys of the entries
        :param hash: either the SQL expression computing the hash of the
            source of an entry from its column ``control``, or the hash
            itself as a string (e.g. a version of the source); with the
            default, the entries stored without ``hash`` are returned
        :return: a dictionary ``{key: value}`` with the values (bytes) of
            the valid entries only
        """
        if not keys:
            return {}
        secret = _get_ir_cache_secret(self.env)

        rows = self.env.execute_query(SQL("""
            SELECT key, control, hash, create_date, signature
              FROM (
                SELECT DISTINCT ON (key) * FROM ir_cache
                 WHERE kind = %s AND key = ANY(%s)
              ORDER BY key, id DESC
            ) entry
             WHERE entry.hash = %s
        """, kind, list(keys), hash))

        # the entries added by this transaction with a read-only cursor (see `_set__`)
        pending = self.env.cr.postcommit.data.get('ir.cache.pending', ())
        pending_rows = {row[2]: (*row[3:5], row[0], row[5]) for row in pending if row[1] == kind and row[2] in keys}
        if pending_rows:
            rows.extend(self.env.execute_query(SQL("""
                SELECT key, control, hash, create_date, signature
                FROM (VALUES %s) AS pending (key, control, hash, create_date, signature)
                WHERE pending.hash = %s
            """, SQL(", ").join(
                SQL("(%s, %s::jsonb, %s, %s::timestamp, %s::bytea)", key, control, hash_, create_date, signature)
                for key, (control, hash_, create_date, signature) in pending_rows.items()
            ), hash)))

        directory = Path(config.cache_dir(self.env.cr.dbname))
        result = {}
        invalid = []
        for key, control, hash_, create_date, signature in rows:
            signature = bytes(signature)
            try:
                data = (directory / _get_ir_cache_filename(kind, create_date, signature)).read_bytes()
            except OSError:
                continue  # e.g. deleted by the GC, or another server without the cache
            message = b'\0'.join([kind.encode(), key.encode(), json.dumps(control, sort_keys=True).encode(), hash_.encode(), data])  # canonical, jsonb does not keep the formatting
            if not hmac_lib.compare_digest(signature, hmac_lib.digest(secret, message, 'sha256')):
                invalid.append(key)
            else:
                result[key] = data
        if invalid and kind != 'ir.cache' and self._check_secret():
            _logger.info("ir.cache: invalid signature of the %s entries %r, ignored", kind, invalid)
        return result

    @api.model
    def _set__(self, kind: str, key: str, value: Buffer, control: list | tuple | dict | None = None, hash: SQL | str = ''):
        """ Add a signed entry for ``value``, with ``hash``, or the hash
        computed by the expression ``hash`` from ``control``. The value is
        written in a file, the entry is added only if the file is written.
        This must be done in the transaction that produced ``value``: when the
        transaction is rolled back, the entry is either rolled back too, or
        does not match its source anymore. With a read-only cursor, the entry is stored by a
        new cursor after the commit, and :meth:`_get` returns it until then.

        :param str kind: the type of the entry, e.g. ``'qweb'``
        :param str key: the key of the entry
        :param value: the bytes to store, e.g. code objects dumped with
            ``marshal``
        :param control: the data identifying the source of the entry, any
            value supported by ``json``, e.g. view ids; the expression
            ``hash`` computes the hash from it, so it requires ``hash`` as
            ``SQL``
        :param hash: either the SQL expression computing the hash of the
            source of the entry from ``control``, or the hash itself as a
            string; with the default, the entry is stored with an empty hash
            and never invalidated
        """
        secret = _get_ir_cache_secret(self.env)

        if bool(control):
            assert isinstance(hash, SQL)
        control_json = json.dumps(control, sort_keys=True)

        hash_value = hash
        if isinstance(hash, SQL):
            [[hash_value]] = self.env.execute_query(SQL("SELECT %s FROM (SELECT %s::jsonb AS control) entry", hash, control_json))

        data = bytes(value)
        message = b'\0'.join([kind.encode(), key.encode(), control_json.encode(), hash_value.encode(), data])  # same as in `_get`

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

        row = (create_date, kind, key, control_json, hash_value, signature)

        if not self.env.cr.readonly:
            self.env.cr.execute(
                SQL("""
                INSERT INTO ir_cache (create_date, kind, key, control, hash, signature)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, *row)
            )
            return

        # A read-only cursor can not write: insert the entries with a new
        # cursor after the commit, `_get` reads them in the meantime. The hash
        # is the one of the source seen by the transaction that produced the
        # value: if the source changed in the meantime, the entry is simply
        # not used.
        rows = self.env.cr.postcommit.data.setdefault('ir.cache.pending', [])
        if not rows:
            registry = self.env.registry

            @self.env.cr.postcommit.add
            def insert_entries():
                try:
                    with registry.cursor() as cr:
                        cr.execute(SQL(
                            "INSERT INTO ir_cache (create_date, kind, key, control, hash, signature) VALUES %s",
                            SQL(", ").join(SQL("(%s, %s, %s, %s, %s, %s)", *row) for row in rows),
                        ))
                except Exception as e:  # noqa: BLE001
                    # the response is already computed, the entries are only a cache
                    _logger.info("ir.cache: failed to store %s entries: %s", len(rows), e)

        rows.append(row)

    @api.model
    def _gc_cache(self):
        """ Called by the cron ``base.ir_cron_ir_cache_gc``, daily and when
        :meth:`_register_hook` finds an invalid canary. When the canary is
        missing or signed with another key, delete all the entries (they may
        be signed with that key too) and their files, and add a new canary. Otherwise delete the entries older than
        ``_cache_max_hours``, except the canary (a deleted entry is simply
        produced again). Then delete the files older than
        ``_cache_max_hours``, except the file of the canary: the files of the
        deleted entries, and the files without entry (e.g. rolled back).
        """
        directory = Path(config.cache_dir(self.env.cr.dbname))
        if not self._check_secret():
            self.env.cr.execute("TRUNCATE ir_cache")
            shutil.rmtree(directory, ignore_errors=True)
            _logger.info("ir.cache: all entries deleted")
            self._set__('ir.cache', 'ir.cache', b'0')
        else:
            self.env.cr.execute(SQL("""
                DELETE FROM ir_cache c
                 WHERE c.create_date < NOW() AT TIME ZONE 'UTC' - make_interval(hours => %s)
                    AND kind != 'ir.cache'
            """, self._cache_max_hours))
            _logger.info("ir.cache: %s entries deleted", self.env.cr.rowcount)

        limit_time = time.time() - self._cache_max_hours * 3600
        count = 0
        for path in directory.iterdir():
            try:
                if not path.name.startswith('ir.cache-') and path.stat().st_mtime < limit_time:
                    path.unlink()
                    count += 1
            except OSError:
                pass  # deleted by another GC
        _logger.info("ir.cache: %s files deleted", count)
