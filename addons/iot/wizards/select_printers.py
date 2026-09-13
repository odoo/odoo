from odoo import fields, models


class SelectPrintersWizard(models.TransientModel):
    _name = "select.printers.wizard"
    _description = "Selection of printers"

    device_ids = fields.Many2many(
        comodel_name="iot.device",
        domain=[("type", "=", "printer")],
    )
    display_device_ids = fields.Many2many(
        comodel_name="iot.device",
        relation="display_device_id_select_printer",
        domain=[("type", "=", "printer")],
    )
    do_not_ask_again = fields.Boolean(
        string="Do not ask me again",
        help="If checked, this dialog won't appear the next time you print and the selected printers will be used automatically.",
    )
