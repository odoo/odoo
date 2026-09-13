from odoo import Command, api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # ------------------
    # Fields declaration
    # ------------------

    display_withholding = fields.Boolean(compute="_compute_display_withholding")
    should_withhold_tax = fields.Boolean(
        string="Withhold Tax Amounts",
        compute="_compute_should_withhold_tax",
        store=True,
        copy=False,
        readonly=False,
        help="Withhold tax amounts from the payment amount.",
    )
    withholding_line_ids = fields.One2many(
        comodel_name="account.payment.withholding.line",
        inverse_name="payment_id",
        string="Withholding Lines",
    )
    withholding_payment_account_id = fields.Many2one(
        related="payment_channel_id.payment_account_id"
    )
    # We may need to manually set an account, for this we want it to not be readonly by default.
    outstanding_account_id = fields.Many2one(readonly=False)
    withholding_hide_tax_base_account = fields.Boolean(
        compute="_compute_withholding_hide_tax_base_account"
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends("company_id")
    def _compute_display_withholding(self):
        """The withholding feature should not show on companies which does not contain any withholding taxes."""
        for company, payments in self.grouped("company_id").items():
            if not company:
                payments.display_withholding = False
                continue

            withholding_taxes = self.env["account.tax"].search(  # noqa: E8507 - one query per company; payments sharing one were merged above
                [
                    *self.env["account.tax"]._check_company_domain(company),
                    ("is_withholding_tax_on_payment", "=", True),
                ]
            )
            for payment in self:
                # To avoid displaying things for nothing, also ensure to only consider withholding taxes matching the payment type.
                payment_domain = self.env[
                    "mixin.account.withholding.line"
                ]._get_domain_withholding_tax(
                    company=payment.company_id, payment_type=payment.payment_type
                )
                payment_withholding_taxes = withholding_taxes.filtered_domain(
                    payment_domain
                )

                payment.display_withholding = bool(payment_withholding_taxes)

    @api.depends("withholding_line_ids")
    def _compute_should_withhold_tax(self):
        """Ensures that we display the line table if any withholding line has been added to the payment."""
        for payment in self:
            payment.should_withhold_tax = bool(payment.withholding_line_ids)

    @api.depends("company_id")
    def _compute_withholding_hide_tax_base_account(self):
        """
        When the withholding tax base account is set in the setting, simplify the view by hiding the account
        column on the lines as we will default to that tax base account.
        """
        for payment in self:
            payment.withholding_hide_tax_base_account = bool(
                payment.company_id.withholding_tax_base_account_id
            )

    @api.depends("should_withhold_tax")
    def _compute_outstanding_account_id(self):
        """Update the computation to reset the account when should_withhold_tax is unchecked."""
        super()._compute_outstanding_account_id()

    # ----------------------------
    # Onchange, Constraint methods
    # ----------------------------

    @api.onchange("withholding_line_ids")
    def _onchange_withholding_line_ids(self):
        """
        Any time a line is edited, we want to check if we need to recompute the placeholders.
        The idea is to try and display accurate placeholders on lines whose tax have a sequence set.
        """
        self.check_singleton()
        if (
            not self.display_withholding
            or not self.withholding_line_ids._is_withholding_lines_placeholder_update_required()
        ):
            return

        self.withholding_line_ids._update_placeholders()

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        # EXTEND account to add the withholding fields in the list.
        return super()._get_trigger_fields_to_synchronize() + (
            "withholding_line_ids",
            "should_withhold_tax",
        )

    def _sync_to_moves(self, changed_fields):
        """Updates the synchronization in order to ensure that the entry takes into account changes in the withholding lines."""
        # EXTEND account
        if not any(
            field_name in changed_fields
            for field_name in self._get_trigger_fields_to_synchronize()
        ):
            return

        withholding_payments = self.filtered(
            lambda payment: payment.withholding_line_ids and payment.should_withhold_tax
        )
        for pay in withholding_payments:
            liquidity_lines, counterpart_lines, write_off_lines = pay._seek_for_lines()

            # `_prepare_move_lines_per_type` calls `_prepare_move_withholding_lines`
            # below and has already reduced the liquidity and counterpart lines by
            # what it returned, so the three arrive balanced and in that order.
            line_vals_list = pay._prepare_move_line_default_vals()
            liquidity_line_values = line_vals_list[0]
            counterpart_line_values = line_vals_list[1]
            write_off_line_ids_commands = [
                Command.create(line_values) for line_values in line_vals_list[2:]
            ]

            line_ids_commands = (
                [
                    Command.update(liquidity_lines.id, liquidity_line_values)
                    if liquidity_lines
                    else Command.create(liquidity_line_values),
                    Command.update(counterpart_lines.id, counterpart_line_values)
                    if counterpart_lines
                    else Command.create(counterpart_line_values),
                ]
                + [Command.delete(line.id) for line in write_off_lines]
                + write_off_line_ids_commands
            )

            pay.move_id.with_context(skip_invoice_sync=True).write(
                {
                    "name": "/",  # Set the name to '/' to allow it to be changed
                    "date": pay.date,
                    "partner_id": pay.partner_id.id,
                    "currency_id": pay.currency_id.id,
                    "partner_bank_id": pay.partner_bank_id.id,
                    "line_ids": line_ids_commands,
                    "journal_id": pay.journal_id.id,
                }
            )

        # All other payments will use the original logic
        super(AccountPayment, self - withholding_payments)._sync_to_moves(
            changed_fields
        )

    def _prepare_move_withholding_lines(self, default_values):
        """Feed the withholding lines to the balance `account` computes for them."""
        # EXTEND account
        if not self.withholding_line_ids or not self.should_withhold_tax:
            return super()._prepare_move_withholding_lines(default_values)
        return self.withholding_line_ids._prepare_withholding_amls_create_values()
