# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountPaymentWithholdingLine(models.Model):
    """
    Database-persisted version of the withholding lines; used on the account.payment model.
    """
    _name = 'account.payment.withholding.line'
    _inherit = "account.withholding.line"
    _description = 'Payment withholding line'
    _check_company_auto = True

    # ------------------
    # Fields declaration
    # ------------------

    payment_id = fields.Many2one(
        comodel_name='account.payment',
        required=True,
        ondelete='cascade',
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('payment_id.amount')
    def _compute_original_amounts(self):
        """ Adds a dependency to the payment amount to ensure recomputation when necessary. """
        super()._compute_original_amounts()

    @api.depends('payment_id.payment_type')
    def _compute_type_tax_use(self):
        for line in self:
            line.type_tax_use = 'sale' if line.payment_id.payment_type == 'inbound' else 'purchase'

    @api.depends('payment_register_id.amount')
    def _compute_comodel_full_amount(self):
        for line in self:
            line.comodel_full_amount = line.payment_register_id.amount

    @api.depends('payment_id.date')
    def _compute_comodel_date(self):
        for line in self:
            line.comodel_date = line.payment_id.date

    @api.depends('payment_id.payment_type')
    def _compute_comodel_payment_type(self):
        for line in self:
            line.comodel_payment_type = line.payment_id.payment_type

    @api.depends('payment_id')
    def _compute_company_id(self):
        for line in self:
            line.company_id = line.payment_id.company_id

    @api.depends('payment_id')
    def _compute_comodel_currency_id(self):
        for line in self:
            line.comodel_currency_id = line.payment_id.currency_id

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    def _prepare_withholding_amls_create_values(self):
        """
        Simply adds a check to ensure that we don't call this method on lines belonging to multiple payments; as it
        is not intended.
        """
        assert len(self.payment_id) == 1, self.env._("All withholding lines in self must have the same payment.")
        return super()._prepare_withholding_amls_create_values()

    # ----------------
    # Business methods
    # ----------------

    def _get_valid_liquidity_accounts(self):
        """
        Get the valid liquidity accounts for the payment;
        If the account of the line matches one of these, the resulting entry will be wrong, thus we need to check the
        account against these to avoid such issue.
        """
        return (
            self.payment_id.journal_id.default_account_id |
            self.payment_id.payment_method_line_id.payment_account_id |
            self.payment_id.journal_id.inbound_payment_method_line_ids.payment_account_id |
            self.payment_id.journal_id.outbound_payment_method_line_ids.payment_account_id |
            self.payment_id.outstanding_account_id
        )
