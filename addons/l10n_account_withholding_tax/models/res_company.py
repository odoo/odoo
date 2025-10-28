# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ------------------
    # Fields declaration
    # ------------------

    withholding_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Withholding Journal",
        help="This journal will be used to record withholding tax entries.",
    )
    withholding_tax_control_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Withholding Tax Control",
        help="This account will be set on withholding tax lines.",
    )
    withhold_applicable_on = fields.Selection(
        selection=[
            ('payment', 'Payment'),
            ('payment_bill', 'Payment and Bill')
        ],
        required=False,
        string="Withholding On",
        help="Determines whether withholding taxes are applied on payments only or on both payments and bills.",
    )
    withhold_applicable = fields.Boolean("Withholding Applicable")
