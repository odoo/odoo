from odoo import models, fields
from odoo.addons import l10n_in_withholding


class AccountMove(l10n_in_withholding.AccountMove):

    l10n_in_withholding_ref_payment_id = fields.Many2one(
        comodel_name='account.payment',
        string="Indian TDS Ref Payment",
        readonly=True,
        copy=False,
        help="Reference Payment for withholding entry",
    )
