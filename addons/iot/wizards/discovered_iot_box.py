from odoo import _, fields, models


class DiscoveredIotBox(models.TransientModel):
    _name = "iot.discovered.box"
    _description = "An IoT box that is in pairing mode"

    name = fields.Char(compute="_compute_name")
    add_iot_box_wizard_id = fields.Many2one(comodel_name="add.iot.box")
    serial_number = fields.Char(readonly=True)
    pairing_code = fields.Char(readonly=True)

    def _compute_name(self):
        for box in self:
            box.name = _(
                "IoT Box %(serial_n)s %(pairing_code)s",
                serial_n=box.serial_number or "",
                pairing_code=box.pairing_code,
            )
