from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_sa_use_branch_crn = fields.Boolean(string='Branch CRN')
