# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # ------------------
    # Fields declaration
    # ------------------

    l10n_account_withholding_line_ids = fields.One2many(
        comodel_name='account.move.line',
        inverse_name='payment_id',
        string='Withholding Lines',
        compute='_l10n_account_withholding_compute_withholding_line_ids',
        readonly=True
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('line_ids')
    def _l10n_account_withholding_compute_withholding_line_ids(self):
        for payment in self:
            payment.l10n_account_withholding_line_ids = payment.line_ids.filtered(lambda p: p.tax_line_id.l10n_account_withholding_type)

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    def write(self, vals):
        # OVERRIDE
        if vals:
            for payment in self.filtered('l10n_account_withholding_line_ids'):
                raise UserError(_("You cannot modify payment %(payment_number)s as it has withholding taxes on it.\n"
                                  "If it is required, please cancel the payment and register a new one.", payment_number=payment.name))
        return super().write(vals)
