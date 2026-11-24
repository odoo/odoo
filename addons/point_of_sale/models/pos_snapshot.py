import inspect
import json
import logging

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import SQL

_logger = logging.getLogger(__name__)


def snapshot(*, version):
    """Store the result of the method for each closed session."""
    def decorator(fn):
        fn._snapshot_version = int(version)
        return fn

    return decorator


class PosSnapshotMixin(models.AbstractModel):
    _name = 'pos.snapshot.mixin'
    _description = 'POS Snapshot Mixin'

    def _snapshot_invalidation_fields(self):
        """Fields that require the snapshots of the session to be rebuilt."""
        return []

    def _snapshot_session_path(self):
        """Path from the record to its POS session."""
        return 'session_id'

    def write(self, vals):
        res = super().write(vals)
        if not vals.keys().isdisjoint(self._snapshot_invalidation_fields()):
            self._snapshot_invalidate()
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_snapshot_invalidate(self):
        self._snapshot_invalidate()

    def _snapshot_sessions(self):
        sessions = self.mapped(self._snapshot_session_path())
        return sessions if isinstance(sessions, models.BaseModel) else self.env['pos.session'].browse(sessions)

    def _snapshot_invalidate(self):
        self.env['pos.snapshot']._enqueue(self._snapshot_sessions())


class PosSnapshot(models.Model):
    """Stored result of a snapshot method for a closed session. Rows without data wait to be built."""
    _name = 'pos.snapshot'
    _description = 'POS Snapshot'
    _log_access = False

    session_id = fields.Many2one('pos.session', required=True, ondelete='cascade')
    key = fields.Char(required=True)  # '<model>.<method>'
    version = fields.Integer(required=True)
    data = fields.Json()

    _session_key_uniq = models.Constraint('UNIQUE(session_id, key)', 'One snapshot per session and key.')
    _pending_idx = models.Index('(session_id) WHERE data IS NULL')

    @api.ormcache(cache='stable')
    def _keys(self):
        """Current version of every snapshot method."""
        keys = {}
        for model in self.env.registry.descendants(['pos.snapshot.mixin'], '_inherit'):
            if model == 'pos.snapshot.mixin':
                continue
            for name, fn in inspect.getmembers(self.env.registry[model], inspect.isfunction):
                if hasattr(fn, '_snapshot_version'):
                    keys[f'{model}.{name}'] = fn._snapshot_version

        return keys

    def _enqueue(self, sessions):
        """Queue the snapshots of closed sessions to be built in the background."""
        session_ids = sessions.filtered(lambda session: session.state == 'closed').ids
        keys = list(self._keys())
        if not session_ids or not keys:
            return
        self.env.cr.execute(SQL(
            """INSERT INTO pos_snapshot (session_id, key, version, data)
            SELECT session_id, key, 0, NULL
            FROM unnest(%s) AS session_id, unnest(%s) AS key
            ON CONFLICT (session_id, key) DO UPDATE SET data = NULL
            WHERE pos_snapshot.data IS NOT NULL""",
            session_ids, keys,
        ))
        if cron := self.env.ref('point_of_sale.ir_cron_pos_daily_maintenance', raise_if_not_found=False):
            cron._trigger()

    def _get(self, key, domain, session_ids):
        """Return the snapshot data of each session, computing it live when it is not stored."""
        model = key.rsplit('.', 1)[0]
        stored = {}
        if session_ids:
            self.env.cr.execute(SQL(
                """SELECT session_id, data FROM pos_snapshot
                    WHERE key = %s AND version = %s AND session_id = ANY(%s) AND data IS NOT NULL""",
                key, self._keys().get(key), list(session_ids),
            ))
            stored = dict(self.env.cr.fetchall())
        live = self.env[model].search(Domain(domain) & Domain(self.env[model]._snapshot_session_path(), 'not in', list(stored)))
        return {
            **{self.env['pos.session'].browse(session_id): data for session_id, data in stored.items()},
            **{session: self._snapshot_method(key)(records) for session, records in live.grouped(lambda r: r._snapshot_sessions()).items()},
        }

    @api.ormcache('key', cache='stable')
    def _snapshot_method(self, key):
        """Return the snapshot method of a key, refusing any other method."""
        model, name = key.rsplit('.', 1)
        fn = dict(inspect.getmembers(self.env.registry[model], inspect.isfunction)).get(name)
        if not hasattr(fn, '_snapshot_version'):
            raise ValueError("Invalid snapshot key: %s" % key)
        return fn

    def _build(self, session_id):
        """Build all snapshots of a session."""
        for key, version in self._keys().items():
            model = key.rsplit('.', 1)[0]
            try:
                with self.env.cr.savepoint():
                    records = self.env[model].search([(self.env[model]._snapshot_session_path(), '=', session_id)])
                    data = self._snapshot_method(key)(records)
                    self.env.cr.execute(SQL(
                        """INSERT INTO pos_snapshot (session_id, key, version, data) VALUES (%s, %s, %s, %s::jsonb)
                           ON CONFLICT (session_id, key) DO UPDATE SET version = EXCLUDED.version, data = EXCLUDED.data""",
                        session_id, key, version, json.dumps(data),
                    ))
            except Exception:
                _logger.warning("POS snapshot %s of session %s failed; computed live.", key, session_id, exc_info=True)
                self.env.cr.execute(SQL(
                    "DELETE FROM pos_snapshot WHERE session_id = %s AND key = %s", session_id, key,
                ))
        # remaining queued rows belong to removed methods, drop them so the cron does not loop
        self.env.cr.execute(SQL("DELETE FROM pos_snapshot WHERE session_id = %s AND data IS NULL", session_id))

    def _cron_build(self):
        """Rebuild outdated snapshots, then build queued sessions one at a time."""
        keys = self._keys()
        self.env.cr.execute(SQL(
            """UPDATE pos_snapshot AS snapshot
               SET version = current.version, data = NULL
               FROM unnest(%s::varchar[], %s::int[]) AS current(key, version)
               WHERE snapshot.key = current.key AND snapshot.version <> current.version""",
            list(keys), list(keys.values()),
        ))
        while True:
            self.env.cr.execute("SELECT session_id FROM pos_snapshot WHERE data IS NULL ORDER BY session_id DESC LIMIT 1")
            row = self.env.cr.fetchone()
            if not row:
                break
            self._build(row[0])
            self.env.cr.execute("SELECT COUNT(DISTINCT session_id) FROM pos_snapshot WHERE data IS NULL")
            remaining = self.env.cr.fetchone()[0]
            if not self.env['ir.cron']._commit_progress(1, remaining=remaining):
                break
