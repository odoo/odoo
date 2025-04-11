# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, api, fields, models, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    # ------------------
    # Fields declaration
    # ------------------

    display_withholding = fields.Boolean(compute='_compute_display_withholding')
    withhold_tax = fields.Boolean(
        string='Withhold Tax Amounts',
        compute='_compute_withhold_tax',
        readonly=False,
        store=True,
    )
    withholding_line_ids = fields.One2many(
        string="Withholding Lines",
        comodel_name='account.payment.register.withholding.line',
        inverse_name='payment_register_id',
        compute='_compute_withholding_lines',
        store=True,
        readonly=False,
    )
    hide_withholding_number_col = fields.Boolean(compute='_compute_hide_withholding_number_col')
    withholding_net_amount = fields.Monetary(
        string='Net Amount',
        help="Net amount after deducting the withholding lines",
        compute='_compute_withholding_net_amount',
        store=True,
    )
    # We need to define the outstanding account of the payment in order for it to have the proper journal entry.
    # To that end, we'll have this field required if we have a withholding tax impacting the payment, and we don't have a payment account set on the payment method.
    default_account_id = fields.Many2one(
        related='journal_id.default_account_id'
    )
    outstanding_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Outstanding Account",
        copy=False,
        domain="[('deprecated', '=', False), '|', ('account_type', 'in', ('asset_current', 'liability_current')), ('id', '=', default_account_id)]",
        check_company=True,
        compute="_compute_outstanding_account_id",
        store=True,
        readonly=False,
    )
    payment_account_id = fields.Many2one(related="payment_method_line_id.payment_account_id")
    payment_move_amount_total = fields.Monetary(
        compute="_compute_payment_move_amount_total",
    )
    hide_tax_base_account = fields.Boolean(compute='_compute_hide_tax_base_account')

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------d

    @api.depends('withholding_line_ids.amount', 'amount')
    def _compute_withholding_net_amount(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                wizard.withholding_net_amount = wizard.amount - sum(wizard.withholding_line_ids.mapped('amount'))
            else:
                wizard.withholding_net_amount = 0.0

    @api.depends('withholding_line_ids.tax_id')
    def _compute_hide_withholding_number_col(self):
        """ When all taxes have default sequences set on them, we can hide the column as it would be readonly & empty. """
        for wizard in self:
            wizard.hide_withholding_number_col = (
                    wizard.withholding_line_ids and
                    all(line.withholding_sequence_id for line in wizard.withholding_line_ids)
            )

    @api.depends('payment_account_id')
    def _compute_outstanding_account_id(self):
        """ We propose a default account by getting one from the latest payment which:
            - Has the same payment method line id (and thus indirectly the same journal, and thus the same company)
            - That payment method has no payment_account_id
            - Yet the payment has an outstanding_account_id
         """
        for wizard in self:
            latest_payment = self.env['account.payment'].search_read(
                domain=[
                    ('payment_method_line_id', '=', wizard.payment_method_line_id.id),
                    ('payment_method_line_id.payment_account_id', '=', False),
                    ('outstanding_account_id', '!=', False),
                ],
                fields=['outstanding_account_id'],
                limit=1,
                order='id desc',
            )
            if wizard.payment_account_id or not latest_payment:
                wizard.outstanding_account_id = False  # we'll use the payment method one.
            else:
                wizard.outstanding_account_id = latest_payment[0]['outstanding_account_id'][0]

    @api.depends('company_id', 'can_edit_wizard', 'can_group_payments', 'group_payment')
    def _compute_display_withholding(self):
        """ We want to hide the withholding tax checkbox in three cases:
         - If there are now withholding taxes in the company;
         - If we are registering payments from multiple entries, where we would end up generating multiple payments;
         - In argentina
        """
        for wizard in self:
            domain = self.env['account.withholding.line']._get_withholding_tax_domain(company=wizard.company_id, payment_type=wizard.payment_type)
            available_withholding_taxes = self.env['account.tax'].search(domain)
            will_create_multiple_entry = not wizard.can_edit_wizard or (wizard.can_group_payments and not wizard.group_payment)
            wizard.display_withholding = available_withholding_taxes and not will_create_multiple_entry and wizard.country_code != 'AR'

    @api.depends('batches')
    def _compute_withholding_lines(self):
        """
        Expected to be called once when opening the wizard, this method will generate the "default" withholding tax lines
        based on the journal entry lines.
        """
        # EXTEND account
        # To compute default withholding values if any lines on the entries has a default withholding tax applied to them.
        super()._compute_from_lines()
        AccountTax = self.env['account.tax']

        for wizard in self:
            if wizard.country_code == 'AR' or not wizard.can_edit_wizard:
                wizard.withholding_line_ids = []
                continue

            batch = wizard.batches[0]
            base_lines = []
            for move in batch['lines'].move_id:
                if move.is_invoice(include_receipts=True):
                    base_amls = move.invoice_line_ids.filtered(lambda line: line.display_type == 'product')
                else:
                    base_amls = move.line_ids.filtered(lambda line: line.display_type == 'product')
                move_base_lines = []
                for line in base_amls:
                    move_base_line = move._prepare_product_base_line_for_taxes_computation(line)
                    move_base_line['calculate_withholding_taxes'] = True
                    move_base_lines.append(move_base_line)
                tax_amls = move.line_ids.filtered('tax_repartition_line_id')
                move_tax_lines = [move._prepare_tax_line_for_taxes_computation(tax_line) for tax_line in tax_amls]
                AccountTax._add_tax_details_in_base_lines(move_base_lines, move.company_id)
                AccountTax._round_base_lines_tax_details(move_base_lines, move.company_id, tax_lines=move_tax_lines)
                base_lines += move_base_lines

            self.withholding_line_ids = self.withholding_line_ids._calculate_withholding_lines_amount(base_lines)

    @api.depends('withholding_line_ids')
    def _compute_withhold_tax(self):
        """ By default, we display the table only if we have default withholding taxes on any products. """
        for wizard in self:
            wizard.withhold_tax = bool(wizard.withholding_line_ids)

    @api.depends('batches')
    def _compute_payment_move_amount_total(self):
        """ Get the full amount of the move related to this wizard.
        We do not use the source_amount as it only takes into account residual amounts.
        """
        def get_total_in_company_currency(move):
            total = sum(line.balance for line in move.line_ids if line.display_type in ('tax', 'product', 'rounding'))
            return move.direction_sign * total

        for wizard in self:
            if wizard.country_code == 'AR' or not wizard.can_edit_wizard:
                wizard.payment_move_amount_total = 0.0
                continue

            # We take the amount in company currency, which will be easier to convert when/if the wizard currency changes.
            move_amount_total = sum(get_total_in_company_currency(move) for move in wizard.batches[0]['lines'].move_id)
            wizard.payment_move_amount_total = move_amount_total

    @api.depends('company_id')
    def _compute_hide_tax_base_account(self):
        for wizard in self:
            wizard.hide_tax_base_account = bool(wizard.company_id.withholding_tax_base_account_id.id)

    # ----------------------------
    # Onchange, Constraint methods
    # ----------------------------

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        """
        Extended in order to apply a similar logic of what is done in super to the custom amounts on the withholding lines.
        """
        # EXTEND account
        super()._onchange_currency_id()
        # It has to be done here as the onchange would not trigger if done in the withholding line model based on the related field.
        for line in self.withholding_line_ids:
            if line.custom_user_amount:
                # We convert from the custom currency id of the wizard to the new currency id.
                line.custom_user_amount = line.base_amount = line.custom_user_currency_id._convert(
                    from_amount=line.custom_user_amount,
                    to_currency=self.currency_id,
                    date=self.payment_date,
                    company=self.company_id,
                )
                # As we handle this on the wizard itself, we can't rely on the onchange to update this.
                line.custom_user_currency_id = self.currency_id

    @api.onchange('withholding_line_ids')
    def _update_withholding_line_amounts(self):
        """ Called in cases when the withholding lines must be updated. """
        self.ensure_one
        AccountTax = self.env['account.tax']
        base_lines = []

        for line in self.withholding_line_ids:
            base_line = line._prepare_base_line_for_taxes_computation()
            AccountTax._add_tax_details_in_base_line(base_line, self.company_id)
            AccountTax._round_base_lines_tax_details([base_line], self.company_id)
            base_lines.append(base_line)

        self.withholding_line_ids = self.withholding_line_ids._calculate_withholding_lines_amount(base_lines)

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    @api.model_create_multi
    def create(self, vals_list):
        """ When selecting an outstanding account manually, we want it to be reconcilable.
        Similarly to what is done on a journal when setting the outstanding account of a payment method, we'll thus mark the
        account as reconcilable if it makes sense.
        """
        # EXTEND account
        for vals in vals_list:
            if vals.get('outstanding_account_id'):
                account = self.env['account.account'].browse(vals['outstanding_account_id'])
                if not account.reconcile and account.account_type not in ('asset_cash', 'liability_credit_card', 'off_balance'):
                    account.reconcile = True
        return super().create(vals_list)

    # ----------------
    # Business methods
    # ----------------

    def _create_payment_vals_from_wizard(self, batch_result):
        # EXTEND 'account'
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        if not self.withholding_line_ids or not self.withhold_tax:
            return payment_vals

        if self.withholding_net_amount < 0:
            raise UserError(_("The withholding net amount cannot be negative."))

        withholding_write_off_line_vals = self.withholding_line_ids._prepare_withholding_line_vals()
        payment_vals['amount'] -= sum(
            abs(line_vals['amount_currency'])
            for line_vals in withholding_write_off_line_vals
            if line_vals.get('tax_repartition_line_id')
        )
        if self.outstanding_account_id:
            payment_vals['outstanding_account_id'] = self.outstanding_account_id.id

        payment_vals['withholding_line_ids'] = []
        withholding_lines_vals = self.withholding_line_ids.with_context(active_test=False).copy_data()
        for withholding_line_vals in withholding_lines_vals:
            del withholding_line_vals['payment_register_id']  # We don't want this on the payment.
            payment_vals['withholding_line_ids'].append(Command.create(withholding_line_vals))

        return payment_vals
