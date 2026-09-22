from odoo import fields, models


class DeviceDataLogReport(models.Model):
    _name = "device.data.log.report"
    _inherit = ["mixin.sql.report", "mixin.materialized.view"]
    _description = "IoT Data Log Analysis Report"
    _auto = False
    _rec_name = "date"
    _order = "date desc, device_id"

    _REPORT_TZ = "America/Mexico_City"

    device_id = fields.Many2one(
        comodel_name="device.device",
        readonly=True,
    )
    device_category_id = fields.Many2one(
        comodel_name="device.kind",
        readonly=True,
    )
    config_id = fields.Many2one(
        comodel_name="device.profile",
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
    )

    date = fields.Date(readonly=True)
    hour = fields.Integer(
        readonly=True,
        aggregator=None,
        help="Hour of day (0-23) for intraday analysis",
    )
    day_of_week = fields.Integer(
        readonly=True,
        aggregator=None,
        help="Day of week (0=Sunday, 6=Saturday)",
    )

    data_type = fields.Selection(
        selection=[
            ("numeric", "Numeric"),
            ("boolean", "Boolean"),
            ("text", "Text"),
            ("json", "JSON"),
        ],
        readonly=True,
    )
    source = fields.Selection(
        selection=[
            ("import", "Imported"),
            ("iot", "IoT Channel"),
            ("manual", "Manual"),
            ("webhook", "Webhook"),
        ],
        readonly=True,
    )

    log_count = fields.Integer(
        readonly=True,
        help="Total number of data points in this aggregation bucket",
    )

    def _get_fields_select(self) -> dict:
        tz = self._REPORT_TZ
        local_ts = f"log.timestamp AT TIME ZONE 'UTC' AT TIME ZONE '{tz}'"
        return {
            "id": f"""ROW_NUMBER() OVER (
                ORDER BY DATE({local_ts}), log.device_id, log.data_type, log.source
            )""",
            "device_id": "log.device_id",
            "device_category_id": "device.device_category_id",
            "config_id": "device.config_id",
            "company_id": "device.company_id",
            "date": f"DATE({local_ts})",
            "hour": f"EXTRACT(HOUR FROM {local_ts})::int",
            "day_of_week": f"EXTRACT(DOW FROM {local_ts})::int",
            "data_type": "log.data_type",
            "source": "log.source",
            "log_count": "COUNT(log.id)",
        }

    def _get_from_tables(self) -> list:
        return [
            ("device_data_log", "log", None, None),
            (
                "device_device",
                "device",
                "LEFT JOIN",
                "log.device_id = device.id",
            ),
        ]

    def _get_where_conditions(self) -> list:
        return [
            "log.device_id IS NOT NULL",
        ]

    def _get_fields_group_by(self) -> list:
        tz = self._REPORT_TZ
        local_ts = f"log.timestamp AT TIME ZONE 'UTC' AT TIME ZONE '{tz}'"
        return [
            "log.device_id",
            "device.device_category_id",
            "device.config_id",
            "device.company_id",
            f"DATE({local_ts})",
            f"EXTRACT(HOUR FROM {local_ts})",
            f"EXTRACT(DOW FROM {local_ts})",
            "log.data_type",
            "log.source",
        ]
