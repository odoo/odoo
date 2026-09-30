# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ------------------
    # Fields declaration
    # ------------------

    withholding_tax_base_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Withholding Tax Base",
        help="This account will be set on withholding tax base lines.",
    )
