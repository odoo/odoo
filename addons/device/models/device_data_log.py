from odoo import api, fields, models


class DeviceDataLog(models.Model):
    _name = "device.data.log"
    _inherit = ["mixin.device.data.log"]
    _description = "Remote Device Data Point"

    _fdw_pointer_columns = (("device_device", "log_last_id"),)

    value_text = fields.Text(help="Text or string data from device")
    value_json = fields.Json(
        help="Structured JSON payload (full device transmission stored as-is)"
    )

    source_topic = fields.Char(
        help="MQTT topic, HTTP endpoint, or protocol URI that delivered this record"
    )
    quality = fields.Selection(
        selection=[
            ("good", "Good"),
            ("bad", "Bad"),
            ("uncertain", "Uncertain"),
        ],
        default="good",
        help="Data quality indicator",
    )

    @api.autovacuum
    def _gc_device_data_logs(self):
        self._gc_old_raw_payloads()
        return self._gc_old_data_logs()
