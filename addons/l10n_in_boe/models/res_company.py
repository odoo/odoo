from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # BOE settings
    l10n_in_boe_feature = fields.Boolean(string="Bill of Entry")
