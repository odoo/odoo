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
        inverse_name='withholding_payment_id',
        string='Withholding Lines',
        compute='_l10n_account_withholding_compute_withholding_line_ids',
        readonly=True
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('move_id.line_ids')
    def _l10n_account_withholding_compute_withholding_line_ids(self):
        for payment in self:
            payment.l10n_account_withholding_line_ids = payment.move_id.line_ids.filtered(lambda p: p.tax_line_id.type_tax_use in {'purchases_wth', 'sales_wth'})

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    @api.model_create_multi
    def create(self, vals_list):
        # We need to provide an account at creation for the move to be correctly generated, but the computation would
        # overwrite the account by the one on the payment method line. While this is a good thing if an account is set on them,
        # it is an issue if it's empty.
        return super(AccountPayment, self.with_context(keep_outstanding_account=True)).create(vals_list)

    def write(self, vals):
        # OVERRIDE
        # These can be changed if needed without impacting the record.
        # We cannot allow changes that would impact the lines directly, because there is no way to get the withholding.
        # info back once the register payment wizard is closed.
        allowed_fields = {'state', 'memo', 'partner_bank_id'}
        significant_changes = any(field not in allowed_fields for field in vals.keys())
        if significant_changes and self.l10n_account_withholding_line_ids:
            raise UserError(_("You cannot modify payments that have withholding taxes on it.\n"
                              "If it is required, please cancel the payment and register a new one."))
        return super().write(vals)
