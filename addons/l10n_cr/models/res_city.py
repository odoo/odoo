from odoo import fields, models


class ResCity(models.Model):
    _inherit = 'res.city'

    l10n_cr_code = fields.Char(string='Cantón Code', size=2, help='Two-digit cantón code within its province.')
