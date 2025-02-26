# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountPaymentWithholdingLine(models.Model):
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

    @api.depends('payment_id.payment_type')
    def _compute_type_tax_use(self):
        for line in self:
            line.type_tax_use = 'sale' if line.payment_id.payment_type == 'inbound' else 'purchase'

    @api.depends('payment_id.amount')
    def _compute_base_amount(self):
        # EXTEND to add the dependency
        super()._compute_base_amount()

    @api.depends('payment_id')
    def _compute_company_id(self):
        for line in self:
            line.company_id = line.payment_id.company_id

    @api.depends('payment_id')
    def _compute_currency_id(self):
        for line in self:
            line.currency_id = line.payment_id.currency_id

    @api.depends('payment_id.original_amount')
    def _compute_comodel_original_amount(self):
        for line in self:
            line.comodel_original_amount = line.payment_id.original_amount

    @api.depends('payment_id.amount')
    def _compute_comodel_amount(self):
        for line in self:
            line.comodel_amount = line.payment_id.amount

    @api.depends('payment_id.date')
    def _compute_comodel_date(self):
        for line in self:
            line.comodel_date = line.payment_id.date

    @api.depends('payment_id.payment_type')
    def _compute_comodel_payment_type(self):
        for line in self:
            line.comodel_payment_type = line.payment_id.payment_type

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    def _prepare_withholding_line_vals_data(self):
        # EXTEND to assert that all lines in self have the same payment when preparing the data to create the payment lines.
        assert len(self.payment_id) == 1, self.env._("All withholding lines in self must have the same payment.")
        return super()._prepare_withholding_line_vals_data()
