# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosPrinter(models.Model):
    _inherit = 'pos.printer'

    printer_type = fields.Selection(
        selection_add=[('imin', 'IMIN')],
        ondelete={'imin': 'set default'},
    )
