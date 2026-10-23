import hashlib
import hmac as hmac_lib
import importlib.util
import json
import logging
import marshal
import sys
import typing
from collections.abc import Callable, Collection

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


class IrCache(models.Model):
    """ Persistent cache of data derived from the database, like the compiled
    code of the QWeb templates, shared by the workers and the restarts.

    The values are stored with :mod:`marshal`, so they may be executable
    (code objects), and anybody may write in the table (ORM, server action,
    SQL injection, psql...): an entry is used only if its signature is
    valid, see :meth:`_get`. The signature is computed with a key that only
    lives in the memory of the server (see :func:`_get_ir_cache_secret`), so a
    valid entry can only be produced by :meth:`_set__`.

    The entries are never updated nor invalidated: a new entry is added for
    the same ``(kind, key)`` and the last one is used if it still matches
    its source: its ``hash`` is computed from its ``control`` by an SQL
    expression given by the caller (specific to the ``kind``), when the
    entry is created and when it is read.

    When the key changes (config admin_passwd, database secret, version of
    Odoo or python), all the entries are deleted at once instead of being
    rejected one by one, see :meth:`_check_secret` and :meth:`_gc_cache`.

    The entries older than ``_cache_max_hours`` are deleted by
    :meth:`_gc_cache` (daily cron): the code producing them (e.g. the QWeb
    compiler) may be fixed without changing the version of Odoo, a fix
    applies to the cached data after that delay plus one day at most.
    """
    _name = 'ir.cache'
    _description = 'Persistent cache'
    _log_access = False
    _allow_sudo_commands = False

    _cache_max_hours = 7*24

    create_date = fields.Datetime(string="Create Date", readonly=True)
    kind = fields.Char(string="Type of the entry", required=True, help="Type of the entry, e.g. 'qweb'")
    key = fields.Char(string="Cache Key", required=True, help="Cache Key, e.g. 'website.layout'")
    control = fields.Json(string="Validation data identifying", required=True, help="Data identifying the source of the entry, e.g. view ids")
    hash = fields.Char(string="Validation Hash", required=True, help="Hash of the source (computed from the control) when the entry was created")
    data = fields.Binary(attachment=False, required=True)
    signature = fields.Binary(attachment=False, required=True)

    _kind_key_idx = models.UniqueIndex('(kind, key, id DESC)')

    def browse(self, ids=()):
        raise SystemError()

    def _register_hook(self):
        """ Check the canary entry. When it is missing or signed with another
        key, trigger :meth:`_gc_cache`, which deletes all the entries.
        """
        super()._register_hook()

        if not self._check_secret():
            if self.env.execute_query(SQL("SELECT id FROM ir_cache WHERE kind = 'ir.cache'")):
                _logger.warning("ir.cache: the key of the signatures changed")
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
    def _get(self, kind: str, keys: Collection[str], hash: SQL | str = '') -> dict[str, typing.Any]:
        """ Return the value of the last entry of each key, if its signature
        is valid and if its source did not change: its ``hash`` is equal to
        ``hash``, or to the expression ``hash`` computed from its ``control``.
        Nothing else is trustworthy: an entry with an invalid signature is
        ignored, and the canary is checked (see :meth:`_check_secret`). The age of the entries is not checked,
        see :meth:`_gc_cache`.

        :param str kind: the type of the entries, e.g. ``'qweb'``
        :param keys: the keys of the entries
        :param hash: either the SQL expression computing the hash of the
            source of an entry from its column ``control``, or the hash
            itself as a string (e.g. a version of the source); with the
            default, the entries stored without ``hash`` are returned
        :return: a dictionary ``{key: value}`` with the valid entries
            only
        """
        if not keys:
            return {}
        secret = _get_ir_cache_secret(self.env)

        rows = self.env.execute_query(SQL("""
            SELECT key, control, hash, data, signature
              FROM (
                SELECT DISTINCT ON (key) * FROM ir_cache
                 WHERE kind = %s AND key = ANY(%s)
              ORDER BY key, id DESC
            ) entry
             WHERE entry.hash = %s
        """, kind, list(keys), hash))

        result = {}
        invalid = []
        for key, control, hash_, data, signature in rows:
            data = bytes(data)
            message = b'\0'.join([kind.encode(), key.encode(), json.dumps(control, sort_keys=True).encode(), hash_.encode(), data])  # canonical, jsonb does not keep the formatting
            if not hmac_lib.compare_digest(bytes(signature), hmac_lib.digest(secret, message, 'sha256')):
                invalid.append(key)
            else:
                result[key] = marshal.loads(data)
        if invalid and kind != 'ir.cache' and self._check_secret():
            _logger.warning("ir.cache: invalid signature of the %s entries %r, ignored", kind, invalid)
        return result

    @api.model
    def _set__(self, kind: str, key: str, value, control: Callable | None=None, hash: SQL | str = ''):
        """ Add a signed entry for ``value``, with ``hash``, or the hash
        computed by the expression ``hash`` from ``control``. This must be
        done in the transaction that produced ``value``: when the transaction
        is rolled back, the entry is either rolled back too, or does not match
        its source anymore. Nothing is stored with a read-only cursor.

        :param str kind: the type of the entry, e.g. ``'qweb'``
        :param str key: the key of the entry
        :param value: any value supported by :mod:`marshal`, e.g. code objects
        :param Callable control: returns the data identifying the source of
            the entry (stored as JSON), e.g. view ids; only called when the
            entry is stored; requires ``hash`` as ``SQL``
        :param hash: either the SQL expression computing the hash of the
            source of the entry from ``control``, or the hash itself as a
            string; with the default, the entry is stored with an empty hash
            and never invalidated
        """
        if self.env.cr.readonly:  # TODO: remove this code so that the cache can be used by read-only controllers
            return
        secret = _get_ir_cache_secret(self.env)

        control_data = None
        if bool(control):
            assert isinstance(hash, SQL)
            control_data = control()
        control_json = json.dumps(control_data)

        hash_value = hash
        if isinstance(hash, SQL):
            [[hash_value]] = self.env.execute_query(SQL("SELECT %s FROM (SELECT %s::jsonb AS control) entry", hash, control_json))

        data = marshal.dumps(value)
        message = b'\0'.join([kind.encode(), key.encode(), json.dumps(control_data, sort_keys=True).encode(), hash_value.encode(), data])  # same as in `_get`
        query = SQL("""
            INSERT INTO ir_cache (create_date, kind, key, control, hash, data, signature)
            VALUES (NOW() AT TIME ZONE 'UTC', %s, %s, %s, %s, %s, %s)
        """, kind, key, control_json, hash_value, data, hmac_lib.digest(secret, message, 'sha256'))
        self.env.cr.execute(query)

    @api.model
    def _gc_cache(self):
        """ Called by the cron ``base.ir_cron_ir_cache_gc``, daily and when
        :meth:`_register_hook` finds an invalid canary. When the canary is
        missing or signed with another key, delete all the entries (they may
        be signed with that key too) and add a new canary. Otherwise delete
        the entries older than ``_cache_max_hours``, except the canary (a
        deleted entry is simply produced again).
        """
        if not self._check_secret():
            self.env.cr.execute("TRUNCATE ir_cache")
            _logger.info("ir.cache: all entries deleted")
            self._set__('ir.cache', 'ir.cache', b'0')
            return

        self.env.cr.execute(SQL("""
            DELETE FROM ir_cache c
             WHERE c.create_date < NOW() AT TIME ZONE 'UTC' - make_interval(hours => %s)
                AND kind != 'ir.cache'
        """, self._cache_max_hours))
        _logger.info("ir.cache: %s entries deleted", self.env.cr.rowcount)
