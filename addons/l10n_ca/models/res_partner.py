from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_ca_pst = fields.Char(string='PST number', help='Canadian Provincial Tax Identification Number')
