# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PosPrinter(models.Model):
    _inherit = 'pos.printer'

    printer_type = fields.Selection(
        selection_add=[('sunmi', 'Sunmi')],
        ondelete={'sunmi': 'set default'}
    )

    @api.constrains('printer_type', 'use_type')
    def _constrains_sunmi_printer(self):
        for record in self:
            if record.printer_type == 'sunmi' and record.use_type != 'receipt':
                raise ValidationError(_("Sunmi printers can only be used as Receipt printers."))
