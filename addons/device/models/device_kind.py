from odoo import fields, models


class DeviceDeviceCategory(models.Model):
    _name = "device.kind"
    _inherit = ["mixin.catalog"]
    _description = "Remote Device Category"
    _order = "sequence, name"

    code = fields.Char(
        required=True,
        help="Technical identifier for this device type",
    )
    sequence = fields.Integer(default=10)
    description = fields.Text(translate=True)

    icon = fields.Char(
        default="fa-microchip",
        help="Font Awesome icon class (e.g., fa-thermometer, fa-wifi)",
    )
    color = fields.Integer(
        default=0,
        help="Color for kanban view",
    )

    comm_protocol = fields.Selection(
        selection=[
            ("http", "HTTP/REST"),
            ("https", "HTTPS/REST"),
        ],
        help="Suggested protocol for this device type",
    )
    link_mode = fields.Selection(
        selection=[
            ("push", "Pushes to Odoo"),
            ("pull", "Odoo dials it"),
            ("stream", "Held open by the stream worker"),
        ],
        help="How devices of this kind and Odoo reach each other, when the "
        "kind knows better than the protocol and the address: a phone pushes "
        "whatever address it carries.",
    )
    disconnect_timeout_seconds = fields.Integer(
        default=0,
        help="Seconds without inbound data before a device is considered stale. "
        "0 = use the global 'device.disconnect_timeout_default' parameter.",
    )

    capabilities = fields.Json(
        help="JSON definition of device capabilities (e.g., sensors, actuators)"
    )

    device_ids = fields.One2many(
        comodel_name="device.device",
        inverse_name="device_category_id",
        help="Devices assigned to this category",
    )
    device_count = fields.Count(
        count_of="device_ids",
        help="Number of devices assigned to this category",
    )

    def write(self, vals):
        result = super().write(vals)
        if "link_mode" in vals:
            self.with_context(active_test=False).device_ids._sync_connection()
        return result

    def action_view_devices(self):
        self.check_singleton()
        return {
            "name": self.env._("Devices: %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "device.device",
            "view_mode": "list,form,kanban",
            "domain": [("device_category_id", "=", self.id)],
            "context": {
                "default_device_category_id": self.id,
                "comm_protocol": self.comm_protocol,
            },
        }
