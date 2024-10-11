from odoo import models, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_in_withholding_ref_payment_id = fields.Many2one(
        comodel_name='account.payment',
        string="Indian TDS Ref Payment",
        readonly=True,
        copy=False,
        help="Reference Payment for withholding entry",
    )
