from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_cz_tax_office_id = fields.Many2one(
        string="Tax Office (CZ)",
        comodel_name='l10n_cz.tax_office',
    )
