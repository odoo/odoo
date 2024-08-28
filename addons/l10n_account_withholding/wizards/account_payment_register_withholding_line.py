# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountPaymentRegisterWithholdingLine(models.TransientModel):
    _name = 'account.payment.register.withholding.line'
    _inherit = "account.withholding.line"
    _description = 'Payment register withholding line'

    # ------------------
    # Fields declaration
    # ------------------

    payment_register_id = fields.Many2one(
        comodel_name='account.payment.register',
        required=True,
        ondelete='cascade',
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('payment_register_id.payment_type')
    def _compute_type_tax_use(self):
        # Override to implement the logic
        for line in self:
            line.type_tax_use = 'sale' if line.payment_register_id.payment_type == 'inbound' else 'purchase'

    @api.depends('payment_register_id.amount')
    def _compute_base_amount(self):
        # Extended to add the dependency
        super()._compute_base_amount()

    @api.depends('payment_register_id')
    def _compute_company_id(self):
        for line in self:
            line.company_id = line.payment_register_id.company_id

    @api.depends('payment_register_id')
    def _compute_currency_id(self):
        for line in self:
            line.currency_id = line.payment_register_id.currency_id

    @api.depends('payment_register_id.payment_move_amount_total')
    def _compute_comodel_original_amount(self):
        for line in self:
            line.comodel_original_amount = line.payment_register_id.payment_move_amount_total

    @api.depends('payment_register_id.amount')
    def _compute_comodel_amount(self):
        for line in self:
            line.comodel_amount = line.payment_register_id.amount

    @api.depends('payment_register_id.payment_date')
    def _compute_comodel_date(self):
        for line in self:
            line.comodel_date = line.payment_register_id.payment_date

    @api.depends('payment_register_id.payment_type')
    def _compute_comodel_payment_type(self):
        for line in self:
            line.comodel_payment_type = line.payment_register_id.payment_type

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    def _prepare_withholding_line_vals_data(self):
        # EXTEND to assert that all lines in self have the same payment register when preparing the data to create the payment lines.
        assert len(self.payment_register_id) == 1, self.env._("All withholding lines in self must have the same payment register.")
        return super()._prepare_withholding_line_vals_data()
