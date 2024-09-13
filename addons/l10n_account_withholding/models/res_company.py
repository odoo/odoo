# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ------------------
    # Fields declaration
    # ------------------

    l10n_account_withholding_tax_base_account_id = fields.Many2one(
        string="Withholding Tax Base Account",
        help="This account will be set on withholding tax base lines.",
        comodel_name='account.account',
        domain=[('deprecated', '=', False)],
    )
