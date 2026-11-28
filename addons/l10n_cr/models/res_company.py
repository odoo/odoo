from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_cr_district_id = fields.Many2one(related='partner_id.l10n_cr_district_id', readonly=False)
