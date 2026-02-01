# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # ------------------
    # Fields declaration
    # ------------------

    display_withholding = fields.Boolean(compute='_compute_display_withholding')
    should_withhold_tax = fields.Boolean(
        string='Withhold Tax Amounts',
        help="Withhold tax amounts from the payment amount.",
        compute='_compute_should_withhold_tax',
        readonly=False,
        store=True,
        copy=False,
    )
    withholding_line_ids = fields.One2many(
        string='Withholding Lines',
        comodel_name='account.payment.withholding.line',
        inverse_name='payment_id',
    )
    withholding_payment_account_id = fields.Many2one(related="payment_method_line_id.payment_account_id")
    # We may need to manually set an account, for this we want it to not be readonly by default.
    outstanding_account_id = fields.Many2one(readonly=False)
    withholding_hide_tax_base_account = fields.Boolean(compute='_compute_withholding_hide_tax_base_account')

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('company_id')
    def _compute_display_withholding(self):
        """ The withholding feature should not show on companies which does not contain any withholding taxes. """
        for company, payments in self.grouped('company_id').items():
            if not company:
                payments.display_withholding = False
                continue

            withholding_taxes = self.env['account.tax'].search([
                *self.env['account.tax']._check_company_domain(company),
                ('is_withholding_tax_on_payment', '=', True),
            ])
            for payment in self:
                # To avoid displaying things for nothing, also ensure to only consider withholding taxes matching the payment type.
                payment_domain = self.env['account.withholding.line']._get_withholding_tax_domain(company=payment.company_id, payment_type=payment.payment_type)
                payment_withholding_taxes = withholding_taxes.filtered_domain(payment_domain)

                payment.display_withholding = bool(payment_withholding_taxes)

    @api.depends('withholding_line_ids')
    def _compute_should_withhold_tax(self):
        """ Ensures that we display the line table if any withholding line has been added to the payment. """
        for payment in self:
            payment.should_withhold_tax = bool(payment.withholding_line_ids)

    @api.depends('company_id')
    def _compute_withholding_hide_tax_base_account(self):
        """
        When the withholding tax base account is set in the setting, simplify the view by hiding the account
        column on the lines as we will default to that tax base account.
        """
        for payment in self:
            payment.withholding_hide_tax_base_account = bool(payment.company_id.withholding_tax_base_account_id)

    @api.depends('should_withhold_tax')
    def _compute_outstanding_account_id(self):
        """ Update the computation to reset the account when should_withhold_tax is unchecked. """
        super()._compute_outstanding_account_id()

    # ----------------------------
    # Onchange, Constraint methods
    # ----------------------------

    @api.onchange('withholding_line_ids')
    def _onchange_withholding_line_ids(self):
        """
        Any time a line is edited, we want to check if we need to recompute the placeholders.
        The idea is to try and display accurate placeholders on lines whose tax have a sequence set.
        """
        self.ensure_one()
        if (
            not self.display_withholding
            or not self.withholding_line_ids._need_update_withholding_lines_placeholder()
        ):
            return

        self.withholding_line_ids._update_placeholders()

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        # EXTEND account
        return super()._get_trigger_fields_to_synchronize() + ('withholding_line_ids', 'should_withhold_tax')

    def _prepare_move_withholding_lines(self, default_values):
        # EXTENDS account
        withholding_lines = super()._prepare_move_withholding_lines(default_values)
        if self.should_withhold_tax and self.withholding_line_ids:
            withholding_lines += self.withholding_line_ids._prepare_withholding_amls_create_values()
        return withholding_lines
