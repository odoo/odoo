# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AddSixTerminal(models.TransientModel):
    _name = "pos_iot_six.add_six_terminal"
    _description = "Connect a Six Payment Terminal"

    iot_box_id = fields.Many2one(
        "iot.box",
        string="IoT Box",
        help="The IoT Box that your Six terminal is connected to.",
        required=True,
        default=lambda self: self._get_existing_iot_box_id()
    )
    iot_box_url = fields.Char(related="iot_box_id.ip_url")
    six_terminal_id = fields.Char(related="iot_box_id.six_terminal_id", readonly=False)
    terminal_device_id = fields.Many2one("iot.device", string="Terminal Device", required=True, default=lambda self: self._get_existing_terminal_device_id())

    def _get_existing_terminal_device_id(self):
        payment_method = self.env["pos.payment.method"].browse(self.env.context["active_id"])
        return payment_method.iot_device_id

    def _get_existing_iot_box_id(self):
        payment_method = self.env["pos.payment.method"].browse(self.env.context["active_id"])
        return payment_method.iot_device_id.iot_id

    @api.onchange("iot_box_id")
    def _on_change_iot_box_id(self):
        if self.terminal_device_id and self.terminal_device_id.iot_id != self.iot_box_id:
            self.terminal_device_id = None

    def action_add_payment_method(self):
        self.ensure_one()
        payment_method = self.env["pos.payment.method"].browse(self.env.context["active_id"])
        payment_method.iot_device_id = self.terminal_device_id
