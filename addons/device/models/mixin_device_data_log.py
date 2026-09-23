import logging
from datetime import timedelta

from odoo import api, fields, models, modules
from odoo.tools import SQL, config

from ..tools import fdw

_logger = logging.getLogger(__name__)


class MixinRemoteDataLog(models.AbstractModel):
    _name = "mixin.device.data.log"
    _description = "Remote Data Point Mixin"
    _order = "timestamp desc, id desc"

    # A concrete log table may be a postgres_fdw foreign table (the GPS log
    # lives in its own database). The ORM cannot manage that schema and
    # Postgres cannot enforce its foreign keys, so _auto_init hands over to
    # tools.fdw: these two attributes tell it which Many2one columns a trigger
    # must verify and which (table, column) pairs point back at this log's id
    # and need the SET NULL behaviour the dropped FK used to give.
    _fdw_checked_references = ("device_id",)
    _fdw_pointer_columns = ()

    device_id = fields.Many2one(
        comodel_name="device.device",
        required=True,
        ondelete="cascade",
        help="Device that generated this data point. Deliberately not index=True: "
        "_device_timestamp_idx below leads with this column, so a btree on it "
        "alone answers nothing the composite does not, and this is the "
        "append-heavy table in the family.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="device_id.company_id",
    )
    timestamp = fields.Datetime(
        default=fields.Datetime.now,
        required=True,
        help="When the data was recorded (device time or receipt time)"
        " Note that this may differ from the record creation time.",
    )
    raw_payload = fields.Text(
        help="Original raw data received from the device, kept for debugging. "
        "Discarded after 'device.raw_payload_retention_days' if that is set; "
        "the parsed columns are unaffected."
    )
    data_type = fields.Selection(
        selection=[
            ("numeric", "Numeric"),
            ("boolean", "Boolean"),
            ("text", "Text"),
            ("json", "JSON"),
        ],
        default="json",
        required=True,
        help="Type of data stored in this record",
    )
    source = fields.Selection(
        selection=[
            ("import", "Imported"),
            ("iot", "IoT Channel"),
            ("manual", "Manual"),
            ("webhook", "Webhook"),
        ],
        default="manual",
        help="Source of this log",
    )

    _device_timestamp_idx = models.Index("(device_id, timestamp DESC, id DESC)")

    def _auto_init(self):
        if self._abstract or not fdw.is_foreign(self.env.cr, self._table):
            return super()._auto_init()
        _logger.info(
            "%s is backed by foreign table %r: syncing its schema through fdw",
            self._name,
            self._table,
        )
        fdw.sync_foreign_schema(self)
        return None

    def _null_pointers_to(self, ids):
        """Clear the columns that point at the given log ids.

        Runs before the rows are deleted so that, on a foreign table, the
        local write lands first and a failure in between leaves a NULL pointer
        rather than a dangling one (the two databases share no transaction).
        """
        if not ids:
            return
        for ptr_table, ptr_column in self._fdw_pointer_columns:
            self.env.cr.execute(
                SQL(
                    "UPDATE %s SET %s = NULL WHERE %s IN %s",
                    SQL.identifier(ptr_table),
                    SQL.identifier(ptr_column),
                    SQL.identifier(ptr_column),
                    tuple(ids),
                )
            )

    def action_view_device(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "res_model": "device.device",
            "res_id": self.device_id.id,
            "view_mode": "form",
            "target": "current",
        }

    _GC_BATCH_SIZE = 5000

    # What the global retention falls back to when nothing is configured. It
    # used to come from device.data_retention_days_default, a seeded parameter
    # 19.0.1.10.0 deleted together with its record, so the second half of that
    # `or` could only ever return this literal.
    _DEFAULT_RETENTION_DAYS = 90

    def _gc_old_logs(self, cutoff_date, domain=None):
        base_domain = [("timestamp", "<", cutoff_date)]
        if domain:
            base_domain.extend(domain)
        obj = self.env[self._name]
        deleted = 0
        while True:
            batch = obj.search(base_domain, limit=self._GC_BATCH_SIZE, order="id")
            if not batch:
                break
            count = len(batch)
            self._null_pointers_to(batch.ids)
            batch.unlink()
            deleted += count
            _logger.info(
                "Cleaning up %s old records from %s older than %s (%s so far)",
                count,
                self._name,
                cutoff_date,
                deleted,
            )
            if not self._is_test_mode():
                self.env["ir.cron"]._commit_progress(count)
            if count < self._GC_BATCH_SIZE:
                break
        return deleted

    def _is_test_mode(self):
        return bool(modules.module.current_test or config["test_enable"])

    _RAW_PAYLOAD_BATCH_SIZE = 20000

    def _gc_old_raw_payloads(self):
        days = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("device.raw_payload_retention_days", default="0")
            or 0
        )
        if days <= 0:
            return 0
        if self._name == "mixin.device.data.log":
            return 0

        cutoff = fields.Datetime.now() - timedelta(days=days)
        cleared = 0
        # Two statements rather than one CTE join: on a foreign table a join
        # between two scans of the same table is executed locally row by row,
        # while a bounded UPDATE ships whole to the remote server.
        while True:
            self.env.cr.execute(
                SQL(
                    """
                    SELECT max(id) FROM (
                        SELECT id FROM %s
                         WHERE timestamp < %s AND raw_payload IS NOT NULL
                         ORDER BY id
                         LIMIT %s
                    ) AS batch
                    """,
                    SQL.identifier(self._table),
                    cutoff,
                    self._RAW_PAYLOAD_BATCH_SIZE,
                )
            )
            bound = self.env.cr.fetchone()[0]
            if bound is None:
                break
            self.env.cr.execute(
                SQL(
                    """
                    UPDATE %s
                       SET raw_payload = NULL
                     WHERE timestamp < %s AND raw_payload IS NOT NULL AND id <= %s
                    """,
                    SQL.identifier(self._table),
                    cutoff,
                    bound,
                )
            )
            written = self.env.cr.rowcount
            if not written:
                break
            cleared += written
            if not self._is_test_mode():
                self.env["ir.cron"]._commit_progress()

        if cleared:
            self.invalidate_model(["raw_payload"])
            _logger.info(
                "Autovacuum: discarded %s raw payload(s) older than %s days from %s",
                cleared,
                days,
                self._name,
            )
        return cleared

    def _gc_old_data_logs(self):
        if self._name == "mixin.device.data.log":
            return True

        parameter = self.env["ir.config_parameter"].sudo()
        retention_days = int(
            parameter.get_param("device.data_retention_days")
            or self._DEFAULT_RETENTION_DAYS
        )

        deleted = 0
        swept_devices = self.env["device.device"]
        profiles = self.env["device.profile"].search([("data_retention_days", ">", 0)])
        for profile in profiles:
            if profile.data_retention_days == retention_days:
                continue
            devices = profile.device_ids
            if not devices:
                continue
            swept_devices |= devices
            deleted += self._gc_old_logs(
                fields.Datetime.now() - timedelta(days=profile.data_retention_days),
                domain=[("device_id", "in", devices.ids)],
            )

        if retention_days <= 0:
            _logger.info("Global data retention is disabled (retention_days <= 0)")
            return True

        cutoff_date = fields.Datetime.now() - timedelta(days=retention_days)
        domain = [("device_id", "not in", swept_devices.ids)] if swept_devices else None
        deleted += self._gc_old_logs(cutoff_date, domain=domain)

        if deleted > 0:
            _logger.info(
                "Autovacuum: deleted %s data point(s) from %s (global retention "
                "%s days, %s profile(s) with their own period)",
                deleted,
                self._name,
                retention_days,
                len(profiles),
            )

        return True

    @api.model
    def get_log_last_ids(self, device, time_window_seconds=15, limit=15):
        cutoff_time = fields.Datetime.now() - timedelta(seconds=time_window_seconds)
        return self.env[self._name].search(
            [
                ("device_id", "=", device.id),
                ("timestamp", ">=", cutoff_time),
            ],
            limit=limit,
            order="timestamp desc, id desc",
        )
