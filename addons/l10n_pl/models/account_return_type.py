from odoo import fields, models


class AccountReturnType(models.Model):
    _inherit = 'account.return.type'

    l10n_pl_repayment_timeframe = fields.Selection(
        string='Repayment Timeframe',
        selection=[
            ('540', '15 days'),
            ('55', '25 days on VAT account'),
            ('56', '25 days on settlement account'),
            ('560', '40 days'),
            ('57', '60 days'),
            ('58', '180 days'),
        ]
    )
