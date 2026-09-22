from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    device_data_retention_days = fields.Integer(
        string="Data Retention (days)",
        default=90,
        config_parameter="device.data_retention_days",
        help="Number of days to keep device data points before auto-cleanup",
    )
    device_raw_payload_retention_days = fields.Integer(
        string="Keep Raw Payloads (days)",
        default=0,
        config_parameter="device.raw_payload_retention_days",
        help="Discard the verbatim device payload on data points older than "
        "this, keeping the row and every parsed column. 0 keeps them forever. "
        "On a busy fleet the payload is the largest thing in the database: "
        "3.1 GB across 6.7M GPS points here, about a third of the whole "
        "database, for a debugging copy of readings that parsed correctly "
        "months ago. Discarding is not reversible.",
    )
    device_disconnect_timeout = fields.Integer(
        string="Disconnect Timeout (seconds)",
        default=300,
        config_parameter="device.disconnect_timeout_default",
        help="Seconds without inbound data before a device is considered "
        "disconnected. The floor: a configuration profile overrides it, and a "
        "device category overrides both.",
    )
    device_polling_interval = fields.Integer(
        string="Poll Devices Every (minutes)",
        compute="_compute_cron_intervals",
        inverse="_inverse_polling_interval",
        help="How often pull-based devices are polled.",
    )
    device_health_check_interval = fields.Integer(
        string="Check Device Health Every (minutes)",
        compute="_compute_cron_intervals",
        inverse="_inverse_health_check_interval",
        help="How often device connection state is recomputed from data recency.",
    )

    @api.depends_context("company")
    def _compute_cron_intervals(self):
        poll = self.env.ref("device.ir_cron_poll_devices", raise_if_not_found=False)
        health = self.env.ref(
            "device.ir_cron_check_device_health", raise_if_not_found=False
        )
        for record in self:
            record.device_polling_interval = self._cron_minutes(poll)
            record.device_health_check_interval = self._cron_minutes(health)

    def _inverse_polling_interval(self):
        for record in self:
            record._write_cron_minutes(
                "device.ir_cron_poll_devices", record.device_polling_interval
            )

    def _inverse_health_check_interval(self):
        for record in self:
            record._write_cron_minutes(
                "device.ir_cron_check_device_health",
                record.device_health_check_interval,
            )

    @api.model
    def _cron_minutes(self, cron):
        if not cron:
            return 0
        factors = {"minute": 1, "hour": 60, "day": 1440, "week": 10080}
        return cron.repeat_interval * factors.get(cron.repeat_unit, 1)

    def _write_cron_minutes(self, xmlid, minutes):
        cron = self.env.ref(xmlid, raise_if_not_found=False)
        if not cron or not minutes or minutes <= 0:
            return
        cron.sudo().write({"repeat_interval": minutes, "repeat_unit": "minute"})
