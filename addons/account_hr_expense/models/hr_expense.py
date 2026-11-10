# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools import clean_context, float_round


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    product_has_tax = fields.Boolean(string="Whether tax is defined on a selected product", compute='_compute_product_has_tax')
    state = fields.Selection(
        selection_add=[
            ('in_payment', 'In Payment'),
        ],
        ondelete={
            'in_payment': lambda expenses: expenses.write({'state': 'paid'}),
        },
    )

    # Split fields
    split_expense_origin_id = fields.Many2one(
        comodel_name='hr.expense',
        string="Origin Split Expense",
        help="Original expense from a split.",
        index='btree_not_null',
    )
    split_expense_ids = fields.One2many(
        comodel_name='hr.expense',
        inverse_name='split_expense_origin_id',
        string="Split Expenses",
    )
    split_expense_count = fields.Integer(string="Number of Split Expenses", compute='_compute_split_expense_count')

    # Accounting fields
    tax_amount_currency = fields.Monetary(
        string="Tax amount in Currency",
        currency_field='currency_id',
        compute='_compute_tax_amount_currency', precompute=True, store=True,
        help="Tax amount in currency",
    )
    tax_amount = fields.Monetary(
        string="Tax amount",
        currency_field='company_currency_id',
        compute='_compute_tax_amount', precompute=True, store=True,
        help="Tax amount in company currency",
    )
    untaxed_amount_currency = fields.Monetary(
        string="Total Untaxed Amount In Currency",
        currency_field='currency_id',
        compute='_compute_tax_amount_currency', precompute=True, store=True,
    )
    untaxed_amount = fields.Monetary(
        string="Total Untaxed Amount",
        currency_field='currency_id',
        compute='_compute_tax_amount', precompute=True, store=True,
    )
    amount_residual = fields.Monetary(
        string="Amount Due",
        currency_field='company_currency_id',
        related='account_move_id.amount_residual', readonly=True,
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        compute='_compute_journal_id',
    )
    selectable_payment_method_line_ids = fields.Many2many(
        comodel_name='account.payment.method.line',
        compute='_compute_selectable_payment_method_line_ids',
        compute_sudo=True,
    )
    payment_method_line_id = fields.Many2one(
        comodel_name='account.payment.method.line',
        string="Payment Method",
        compute='_compute_payment_method_line_id', store=True, index=True, readonly=False,
        domain="[('id', 'in', selectable_payment_method_line_ids)]",
        help="The payment method used when the expense is paid by the company.",
    )
    has_existing_bill = fields.Boolean(
        help=""" - When a bill already exists, the payment will use the supplier payable account so it can be matched with the bill.
                 - When no bill exists, the payment will be recorded directly on the expense account, as usual.
            """
    )
    account_move_id = fields.Many2one(
        string="Journal Entry",
        comodel_name='account.move',
        readonly=True,
        copy=False,
        index='btree_not_null',
    )
    account_move_state = fields.Selection(related='account_move_id.state', string="Journal Entry Status")
    account_id = fields.Many2one(
        comodel_name='account.account',
        string="Account",
        compute='_compute_account_id', precompute=True, store=True, readonly=False,
        check_company=True,
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card'))]",
        help="An expense account is expected for employee paid expenses and company paid expenses without a matched bill.\n"
             "For company paid expenses with a matched bill, the account needs to be the payable account of the bill.",
    )
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        relation='expense_tax',
        column1='expense_id',
        column2='tax_id',
        string="Included taxes",
        compute='_compute_tax_ids', precompute=True, store=True, readonly=False,
        domain="[('type_tax_use', '=', 'purchase')]",
        check_company=True,
        help="Both price-included and price-excluded taxes will behave as price-included taxes for expenses.",
    )

    # Security fields
    can_edit_account = fields.Boolean(compute='_compute_can_edit_account')

    # --------------------------------------------
    # Constraints
    # --------------------------------------------

    @api.constrains('account_move_id')
    def _check_o2o_payment(self):
        for expense in self:
            if len(expense.account_move_id.origin_payment_id.expense_ids) > 1:
                raise ValidationError(self.env._("Only one expense can be linked to a particular payment"))

    # --------------------------------------------
    # Compute methods
    # --------------------------------------------

    @api.depends('product_id')
    def _compute_product_has_tax(self):
        for expense in self:
            expense.product_has_tax = bool(
                expense.product_id.supplier_taxes_id.filtered_domain(self.env['account.tax']._check_company_domain(expense.company_id))
            )

    @api.depends(
        'amount_residual',
        'account_move_id.state',
        'account_move_id.payment_state',
        'account_move_id.origin_payment_id.is_matched',
    )
    def _compute_state(self):
        # EXTEND hr_expense
        super()._compute_state()

    @api.depends('quantity', 'price_unit', 'tax_ids')
    def _compute_total_amount_currency(self):
        # OVERRIDE hr_expense when taxes are found
        expenses_with_taxes = self.filtered('tax_ids')
        AccountTax = self.env['account.tax']
        for expense in expenses_with_taxes.filtered('product_has_cost'):
            base_line = expense._prepare_base_line_for_taxes_computation(price_unit=expense.price_unit, quantity=expense.quantity)
            AccountTax._add_tax_details_in_base_line(base_line, expense.company_id)
            AccountTax._round_base_lines_tax_details([base_line], expense.company_id)
            expense.total_amount_currency = base_line['tax_details']['total_included_currency']
        super(HrExpense, self - expenses_with_taxes)._compute_total_amount_currency()

    @api.depends(
        'date',
        'company_id',
        'currency_id',
        'company_currency_id',
        'is_multiple_currency',
        'total_amount_currency',
        'product_id',
        'employee_id.user_id.partner_id',
        'quantity',
    )
    def _compute_total_amount(self):
        AccountTax = self.env['account.tax']
        for expense in self:
            if not expense.company_id:
                # This would be happening when emptying the required company_id field, triggering the "onchange"s.
                # A traceback would occur because company_currency_id would be set to False.
                # Instead of using the env company, recomputing the interface just to be blocked when trying to save
                # we choose not to recompute anything and wait for a proper company to be inputted.
                continue

            if expense.is_multiple_currency:
                base_line = expense._prepare_base_line_for_taxes_computation(
                    price_unit=expense.total_amount_currency * expense.currency_rate,
                    quantity=1.0,
                    currency_id=expense.company_currency_id,
                    rate=1.0,
                )
                AccountTax._add_tax_details_in_base_line(base_line, expense.company_id)
                AccountTax._round_base_lines_tax_details([base_line], expense.company_id)
                expense.total_amount = base_line['tax_details']['total_included_currency']
            else:  # Mono-currency case computation shortcut
                expense.total_amount = expense.total_amount_currency

    def _inverse_total_amount(self):
        super()._inverse_total_amount()
        AccountTax = self.env['account.tax']
        for expense in self:
            if expense.is_multiple_currency:
                base_line = expense._prepare_base_line_for_taxes_computation(
                    price_unit=expense.total_amount,
                    quantity=1.0,
                    currency=expense.company_currency_id,
                )
                AccountTax._add_tax_details_in_base_line(base_line, expense.company_id)
                AccountTax._round_base_lines_tax_details([base_line], expense.company_id)
                tax_details = base_line['tax_details']
                expense.tax_amount = tax_details['total_included_currency'] - tax_details['total_excluded_currency']
                expense.untaxed_amount = tax_details['total_excluded_currency']
            else:
                expense.total_amount_currency = expense.total_amount
                expense.tax_amount = expense.tax_amount_currency
                expense.untaxed_amount = expense.untaxed_amount_currency
            expense.currency_rate = expense.total_amount / expense.total_amount_currency if expense.total_amount_currency else 1.0
            expense.price_unit = expense.total_amount / expense.quantity if expense.quantity else expense.total_amount

    @api.depends('product_id', 'company_id')
    def _compute_tax_ids(self):
        for expense in self.filtered('company_id'):  # Avoid a traceback, the field is required anyway
            expense = expense.with_company(expense.company_id)
            # taxes only from the same company
            expense.tax_ids = expense.product_id.supplier_taxes_id.filtered_domain(
                self.env['account.tax']._check_company_domain(expense.company_id)
            )

    @api.depends('split_expense_origin_id')
    def _compute_split_expense_count(self):
        if not self.split_expense_origin_id:
            self.split_expense_count = 0
            return
        count_per_expense_origin_id = {
            expense.id: count
            for expense, count in self.env['hr.expense']._read_group(
                domain=[('split_expense_origin_id', 'in', self.split_expense_origin_id.ids)],
                groupby=['split_expense_origin_id'],
                aggregates=['__count'],
            )
        }
        for expense in self:
            expense.split_expense_count = count_per_expense_origin_id.get(expense.split_expense_origin_id.id, 0)

    @api.depends('total_amount_currency', 'tax_ids')
    def _compute_tax_amount_currency(self):
        """
             Note: as total_amount_currency can be set directly by the user (for product without cost)
             or needs to be computed (for product with cost), `untaxed_amount_currency` can't be computed in the same method
             as `total_amount_currency`.
        """
        AccountTax = self.env['account.tax']
        for expense in self:
            if not expense.company_id:
                # This would be happening when emptying the required company_id field, triggering the "onchange"s.
                # A traceback would occur because company_currency_id would be set to False.
                # Instead of using the env company, recomputing the interface just to be blocked when trying to save
                # we choose not to recompute anything and wait for a proper company to be inputted.
                continue

            base_line = expense._prepare_base_line_for_taxes_computation(
                price_unit=expense.total_amount_currency,
                quantity=1.0,
            )
            AccountTax._add_tax_details_in_base_line(base_line, expense.company_id)
            AccountTax._round_base_lines_tax_details([base_line], expense.company_id)
            tax_details = base_line['tax_details']
            expense.tax_amount_currency = tax_details['total_included_currency'] - tax_details['total_excluded_currency']
            expense.untaxed_amount_currency = tax_details['total_excluded_currency']

    @api.depends('total_amount', 'currency_rate', 'tax_ids', 'is_multiple_currency')
    def _compute_tax_amount(self):
        """
             Note: as total_amount can be set directly by the user when the currency_rate is overridden,
             the tax must be computed after the total_amount.
        """
        AccountTax = self.env['account.tax']
        for expense in self:
            if not expense.company_id:
                # This would be happening when emptying the required company_id field, triggering the "onchange"s.
                # A traceback would occur because company_currency_id would be set to False.
                # Instead of using the env company, recomputing the interface just to be blocked when trying to save
                # we choose not to recompute anything and wait for a proper company to be inputted.
                continue

            if expense.is_multiple_currency:
                base_line = expense._prepare_base_line_for_taxes_computation(
                    price_unit=expense.total_amount,
                    quantity=1.0,
                    currency=expense.company_currency_id,
                )
                AccountTax._add_tax_details_in_base_line(base_line, expense.company_id)
                AccountTax._round_base_lines_tax_details([base_line], expense.company_id)
                tax_details = base_line['tax_details']
                expense.tax_amount = tax_details['total_included_currency'] - tax_details['total_excluded_currency']
                expense.untaxed_amount = tax_details['total_excluded_currency']
            else:  # Mono-currency case computation shortcut
                expense.tax_amount = expense.tax_amount_currency
                expense.untaxed_amount = expense.untaxed_amount_currency

    @api.depends('selectable_payment_method_line_ids')
    def _compute_payment_method_line_id(self):
        for expense in self:
            expense.payment_method_line_id = expense.selectable_payment_method_line_ids[:1]

    @api.depends('company_id')
    def _compute_selectable_payment_method_line_ids(self):
        for expense in self:
            allowed_method_line_ids = expense.company_id.company_expense_allowed_payment_method_line_ids
            if allowed_method_line_ids:
                expense.selectable_payment_method_line_ids = allowed_method_line_ids
            else:
                expense.selectable_payment_method_line_ids = self.env['account.payment.method.line'].search([
                    # The journal is the source of the payment method line company
                    *self.env['account.journal']._check_company_domain(expense.company_id),
                    ('payment_type', '=', 'outbound'),
                    ('journal_id.active', '=', True),
                ])

    @api.depends('product_id', 'company_id', 'has_existing_bill', 'vendor_id')
    def _compute_account_id(self):
        for expense in self:
            expense = expense.with_company(expense.company_id)
            account = False

            if expense.has_existing_bill:
                account = expense.vendor_id.commercial_partner_id.property_account_payable_id or expense.company_id.payable_account_id

            elif expense.product_id:
                account = expense.product_id.product_tmpl_id._get_product_accounts()['expense']

            expense.account_id = account or expense.company_id.expense_account_id

    @api.depends('product_id', 'account_id', 'employee_id')
    def _compute_analytic_distribution(self):
        # EXTENDS hr_expense to add account dependency
        super()._compute_analytic_distribution()

    @api.depends_context('uid')
    @api.depends('state')
    def _compute_can_edit_account(self):
        if not self.env.user.has_group('account.group_account_invoice'):
            self.can_edit_account = False
        else:
            for expense in self:
                expense.can_edit_account = expense.state == 'approved'

    @api.depends('payment_mode', 'payment_method_line_id')
    def _compute_journal_id(self):
        for expense in self:
            if expense.payment_mode == 'company_account':
                expense.journal_id = expense.payment_method_line_id.journal_id
            elif expense.payment_mode == 'own_account':
                expense.journal_id = expense._get_default_journal()
            else:
                expense.journal_id = False

    # ----------------------------------------
    # ORM Overrides
    # ----------------------------------------

    def write(self, vals):
        edited_fields = set(vals)
        readonly_expenses = self.filtered(lambda e: not e.is_editable)
        if not self.env.su and not self.env.user.has_group('account.group_account_invoice') and readonly_expenses:
            if 'tax_ids' in edited_fields:
                raise UserError(self.env._(
                    "Uh-oh! You can’t edit this expense.\n\n"
                    "Reach out to the administrators, flash your best smile, and see if they'll grant you the magical access you seek.",
                ))

        if vals.get('marked_as_paid'):
            raise UserError(self.env._("Expense can't be manually marked as paid without an accounting entry."))

        return super().write(vals)

    # --------------------------------------------
    # Mail Thread
    # --------------------------------------------

    def _get_track_log_reimbursed_amount(self):
        # EXTEND hr_expense
        return super()._get_track_log_reimbursed_amount() - self.amount_residual

    def _track_log_get_default_subtype(self, track_init_values):
        self.ensure_one()
        if 'state' not in track_init_values:
            return super()._track_log_get_default_subtype(track_init_values)

        if self.state == 'approved':
            if track_init_values['state'] in self._get_in_payment_states():  # Reverting state
                subtype = 'account_hr_expense.mt_expense_entry_draft' if self.account_move_id else 'account_hr_expense.mt_expense_entry_delete'
                return self.env.ref(subtype)
            return self.env.ref('hr_expense.mt_expense_approved')
        else:
            return super()._track_log_get_default_subtype(track_init_values)

    @api.model
    def _get_mail_gateway_vals(self, product, company):
        vals = {
            **super()._get_mail_gateway_vals(product, company),
            'tax_ids': [Command.set(product.supplier_taxes_id.filtered(lambda r: r.company_id == company).ids)],
        }
        account = product.product_tmpl_id._get_product_accounts()['expense']
        if account:
            vals['account_id'] = account.id
        return vals

    # ----------------------------------------
    # Actions
    # ----------------------------------------

    def action_pay(self):
        # OVERRIDE hr_expense
        self._check_can_pay()
        return self.account_move_id.with_context(default_partner_bank_id=(
            self.account_move_id.partner_bank_id.id if len(self.account_move_id.partner_bank_id) <= 1 else None
        )).action_register_payment()

    def action_open_split_expense(self):
        self.ensure_one()
        split_expense_ids = self.search([('split_expense_origin_id', '=', self.split_expense_origin_id.id)])
        return split_expense_ids._get_records_action(name=self.env._("Split Expenses"))

    def action_split_wizard(self):
        self.ensure_one()
        if self.filtered(lambda expense: expense.state in self._get_in_payment_states()):
            raise UserError(self.env._("You cannot split an expense that is already paid."))
        if not self.is_editable:
            raise UserError(self.env._("You do not have the rights to edit this expense."))

        splits = self.env['hr.expense.split'].create(self._get_split_values())

        wizard = self.env['hr.expense.split.wizard'].create([{
            'expense_split_line_ids': splits.ids,
            'expense_id': self.id,
        }])
        return {
            'name': self.env._("Expense split"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [[False, "form"]],
            'res_model': 'hr.expense.split.wizard',
            'res_id': wizard.id,
            'target': 'new',
            'context': self.env.context,
        }

    def action_open_account_move(self):
        self.ensure_one()
        return self._open_linked_record('account.move', self.account_move_id)

    def action_open_account_payment(self):
        self.ensure_one()
        return self._open_linked_record('account.payment', self.account_move_id.origin_payment_id)

    # ----------------------------------------
    # Business
    # ----------------------------------------

    def _get_analytic_extra_data(self):
        self.ensure_one()
        return super()._get_analytic_extra_data() | {
            'account_prefix': self.account_id.code,
            'product_id': self.product_id.id,
            'product_categ_id': self.product_id.categ_id.id,
        }

    def _get_distribution_validation_kwargs(self):
        # EXTEND hr_expense
        return {**super()._get_distribution_validation_kwargs(), 'account': self.account_id.id}

    @api.model
    def _get_pay_group(self):
        # OVERRIDE hr_expense: paying goes through the payment wizard, which needs accounting rights
        return 'account.group_account_invoice'

    @api.model
    def _get_in_payment_states(self):
        return ('in_payment',) + super()._get_in_payment_states()

    def _get_duplicate_exemption_ids(self):
        # EXTEND hr_expense: the expenses of a split share the receipt of the original one
        return super()._get_duplicate_exemption_ids() | set(self.split_expense_origin_id.split_expense_ids.ids)

    @api.model
    def _open_linked_record(self, res_model, record):
        return {
            'type': 'ir.actions.act_window',
            'res_model': res_model,
            'name': record.name,
            'view_mode': 'form',
            'res_id': record.id,
            'views': [(False, 'form')],
        }

    def _check_can_reset_approval(self):
        super()._check_can_reset_approval()
        if any(state not in {False, 'draft'} for state in self.account_move_id.mapped('state')):
            raise UserError(self.env._("You cannot reset to draft an expense linked to a journal entry."))

    def _check_can_create_move(self):
        if any(expense.state != 'approved' for expense in self):
            raise UserError(self.env._("You can only generate an accounting entry for approved expense(s)."))

        if False in self.mapped('payment_mode'):
            raise UserError(self.env._("Please specify if the expenses were paid by the company or reimbursed to the employee directly."))

    def _do_approve(self):
        # EXTEND hr_expense add move creation
        expenses_to_approve = self.filtered(lambda s: s.state in {'submitted', 'draft'})
        super()._do_approve()
        expenses_to_approve._create_move()

    def _get_company_paid_move_creation_context(self):
        """
        Hook to get a specific context for move creation of company paid expenses,
        will be used to create move and payment of company paid expenses.
        """
        return {}

    def _create_move(self):
        self._check_can_create_move()

        company_expenses, employee_expenses = self.partitioned(lambda expense: expense.payment_mode == 'company_account')
        if len(employee_expenses.company_id) > 1:
            raise UserError(self.env._("You can't create move for employee-paid expenses belonging to different companies at the same time"))

        for expense in self.with_context(validate_analytic=True):
            expense._validate_distribution(**expense._get_distribution_validation_kwargs())

        if company_expenses:
            company_paid_context = {**clean_context(self.env.context), **self._get_company_paid_move_creation_context()}  # clean_context to remove default_*
            # sale_project computes the analytic distribution of the lines from the `project_id` of the context (opw-6326551).
            # Dropping the key here avoids a bridge module between the project and account modules.
            company_paid_context.pop('project_id', None)
            # Creation of the account moves for the company-paid expenses.
            # For company-paid expenses using SEPA Credit Transfer, the vendor must be set
            # because SEPA XML generation requires a creditor name (partner).
            expenses_missing_vendor = company_expenses.filtered(
                lambda exp: exp.payment_method_line_id.code == 'sepa_ct' and not exp.vendor_id
            )
            if expenses_missing_vendor:
                raise RedirectWarning(
                    message=self.env._(
                        "The vendor is required for expenses using SEPA Credit Transfer as the payment method."
                        "\nPlease set a vendor on the expenses."
                    ),
                    action=expenses_missing_vendor._get_records_action(),
                    button_text=self.env._("Go to expense(s)"),
                )

            # -> Create an account payment (we only "log" the already paid expense so it can be reconciled)
            move_vals_list, payment_vals_list = zip(*[expense._prepare_payments_vals() for expense in company_expenses])

            payment_moves_sudo = self.with_context(company_paid_context).env['account.move'].sudo().create(move_vals_list)
            for payment_vals, move in zip(payment_vals_list, payment_moves_sudo):
                payment_vals['move_id'] = move.id

            payments_sudo = self.with_context(company_paid_context).env['account.payment'].sudo().create(payment_vals_list)
            for payment, move in zip(payments_sudo, payment_moves_sudo):
                move.update({
                    'origin_payment_id': payment.id,
                    # We need to put the journal_id because editing origin_payment_id triggers a re-computation chain
                    # that voids the company_currency_id of the lines
                    'journal_id': move.journal_id.id,
                })

        if employee_expenses:
            # Creation of the account moves for the employee paid expenses.
            existing_bill_expenses, no_bill_expenses = employee_expenses.partitioned('has_existing_bill')
            existing_bill_expenses._create_entry_for_expense_with_linked_bill()

            if no_bill_expenses:
                journal = no_bill_expenses[0]._get_default_journal()
                today = fields.Date.context_today(self)
                expense_receipt_vals_list = [{
                    **new_receipt_vals,
                    'journal_id': journal.id,
                    'invoice_date': today,
                } for new_receipt_vals in no_bill_expenses._prepare_receipts_vals()]
                moves_sudo = self.with_context(clean_context(self.env.context)).env['account.move'].sudo().create(expense_receipt_vals_list)  # clean_context to remove default_*
                for move_sudo in moves_sudo:
                    move_sudo._message_set_main_attachment_id(move_sudo.attachment_ids, force=True, filter_xml=False)

    def _do_reset_approval(self):
        # EXTEND hr_expense to delete the draft entries, `_check_can_reset_approval` refuses the others
        expenses = self.with_context(clean_context(self.env.context))
        expenses.sudo().account_move_id.unlink()  # Sudo as approvers may not be accountants
        return super(HrExpense, expenses)._do_reset_approval()

    def _do_refuse(self, reason):
        # Sudoed as approvers may not be accountants
        draft_moves_sudo = self.sudo().account_move_id.filtered(lambda move: move.state == 'draft')
        if self.sudo().account_move_id - draft_moves_sudo:
            raise UserError(self.env._("You cannot cancel an expense linked to a journal entry"))

        if draft_moves_sudo:
            draft_moves_sudo.unlink()  # Else we have lingering moves
        super()._do_refuse(reason)

    def _get_split_values(self):
        self.ensure_one()
        half_price = self.total_amount_currency / 2
        price_round_up = float_round(half_price, precision_digits=self.currency_id.decimal_places, rounding_method='UP')
        price_round_down = float_round(half_price, precision_digits=self.currency_id.decimal_places, rounding_method='DOWN')

        return [{
            'name': self.name,
            'product_id': self.product_id.id,
            'total_amount_currency': price,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'analytic_distribution': self.analytic_distribution,
            'employee_id': self.employee_id.id,
            'tax_ids': [Command.set(self.tax_ids.ids)],
            'approval_state': self.approval_state,
            'approval_date': self.approval_date,
            'manager_id': self.manager_id.id,
            'expense_id': self.id,
        } for price in (price_round_up, price_round_down)]

    def _get_paid_status(self):
        # OVERRIDE hr_expense: the status of expenses with an entry follows it, even for company paid ones
        self.ensure_one()
        move = self.account_move_id
        if not move:
            return ''  # The expense isn't paid

        if move.state == 'cancel':
            return 'paid'

        if self.payment_mode == 'company_account':
            # Shortcut to paid, as it's already paid, but we may not have the bank statement yet
            return 'paid'
        elif move.state == 'draft':
            return 'approved'
        elif self.has_existing_bill:
            # The entry is the payment to the employee, the bill is settled by the debt transfer entry
            return 'paid' if move.origin_payment_id.is_matched else self.env['account.move']._get_invoice_in_payment_state()
        elif move.payment_state == 'not_paid':
            return 'approved'  # A posted receipt still waits for its payment
        elif (
            move.payment_state == 'in_payment'
            or (move.payment_state == 'partial' and not self.company_currency_id.is_zero(self.amount_residual))
        ):
            return self.env['account.move']._get_invoice_in_payment_state()
        else:  # Partial, reversed or paid
            return 'paid'

    def _prepare_receipts_vals(self):
        return_vals = []
        for employee_sudo, expenses_sudo in self.sudo().grouped('employee_id').items():
            attachments_data = [
                Command.create(attachment.copy_data({'res_model': 'account.move', 'res_id': False, 'raw': attachment.raw})[0])
                for attachment in expenses_sudo.attachment_ids
            ]
            multiple_expenses_name = self.env._("Expenses of %(employee)s", employee=employee_sudo.name)
            move_ref = expenses_sudo.name if len(expenses_sudo) == 1 else multiple_expenses_name
            return_vals.append({
            **expenses_sudo._prepare_move_vals(),
                'ref': move_ref,
                'move_type': 'in_receipt',
                'partner_id': employee_sudo.work_contact_id.id,
                'commercial_partner_id': employee_sudo.user_partner_id.id,
                'currency_id': expenses_sudo.company_currency_id.id,
                'company_id': expenses_sudo.company_id.id,
                'line_ids': [Command.create(expense_sudo._prepare_move_lines_vals()) for expense_sudo in expenses_sudo],
                'partner_bank_id': employee_sudo.primary_bank_account_id.id,
                'attachment_ids': attachments_data,
            })
        return return_vals

    def _prepare_payments_vals(self):
        self.ensure_one()

        journal = self.journal_id
        payment_method_line = self.payment_method_line_id
        if not payment_method_line:
            raise UserError(self.env._("You need to add a manual payment method on the journal (%s)", journal.name))

        if self.has_existing_bill:
            return self._prepare_linked_bill_payment_vals()

        AccountTax = self.env['account.tax']
        rate = abs(self.total_amount_currency / self.total_amount) if self.total_amount else 0.0
        base_line = self._prepare_base_line_for_taxes_computation(
            price_unit=self.total_amount_currency,
            quantity=1.0,
            account_id=self._get_base_account(),
            rate=rate,
        )
        base_lines = [base_line]
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, self.company_id)
        AccountTax._add_accounting_data_in_base_lines_tax_details(base_lines, self.company_id, include_caba_tags=self.payment_mode == 'company_account')
        tax_results = AccountTax._prepare_tax_lines(base_lines, self.company_id)

        # Base line.
        move_lines = []
        base_move_line = {}
        for base_line, to_update in tax_results['base_lines_to_update']:
            base_move_line = {
                'name': self._get_move_line_name(),
                'account_id': base_line['account_id'].id,
                'product_id': base_line['product_id'].id,
                'analytic_distribution': base_line['analytic_distribution'],
                'expense_id': self.id,
                'tax_ids': [Command.set(base_line['tax_ids'].ids)],
                'tax_tag_ids': to_update['tax_tag_ids'],
                'amount_currency': to_update['amount_currency'],
                'balance': to_update['balance'],
                'currency_id': base_line['currency_id'].id,
                'partner_id': self.vendor_id.id,
            }
            move_lines.append(base_move_line)

        # Tax lines.
        total_tax_line_balance = 0.0
        for tax_line in tax_results['tax_lines_to_add']:
            total_tax_line_balance += tax_line['balance']
            move_lines.append(tax_line)
        base_move_line['balance'] = self.total_amount - total_tax_line_balance

        # Outstanding payment line.
        move_lines.append({
            'name': self._get_move_line_name(),
            'account_id': self._get_expense_account_destination(),
            'balance': -self.total_amount,
            'amount_currency': self.currency_id.round(-self.total_amount_currency),
            'currency_id': self.currency_id.id,
            'partner_id': self.vendor_id.id,
        })
        payment_vals = {
            'date': self.date,
            'memo': self.name,
            'journal_id': journal.id,
            'amount': self.total_amount_currency,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': self.vendor_id.id,
            'currency_id': self.currency_id.id,
            'payment_method_line_id': payment_method_line.id,
            'company_id': self.company_id.id,
        }
        move_vals = {
            **self._prepare_move_vals(),
            'date': self.date or fields.Date.context_today(self),
            'ref': self.name,
            'journal_id': journal.id,
            'partner_id': self.vendor_id.id,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'line_ids': [Command.create(line) for line in move_lines],
            'attachment_ids': [
                Command.create(attachment.copy_data({'res_model': 'account.move', 'res_id': False, 'raw': attachment.raw})[0])
                for attachment in self.attachment_ids]
        }
        return move_vals, payment_vals

    def _prepare_linked_bill_payment_vals(self):
        self.ensure_one()

        move_lines = [
            # Debit: The Payable Account (neutralizing the debt of the original bill)
            {
                'name': self._get_move_line_name(),
                'account_id': self.account_id.id,
                'expense_id': self.id,
                'amount_currency': self.total_amount_currency,
                'balance': self.total_amount,
                'currency_id': self.currency_id.id,
                'partner_id': self.vendor_id.id,
            },
            # Credit: Outstanding Payments
            {
                'name': self._get_move_line_name(),
                'account_id': self._get_expense_account_destination(),
                'amount_currency': -self.total_amount_currency,
                'balance': -self.total_amount,
                'currency_id': self.currency_id.id,
                'partner_id': self.vendor_id.id,
            }
        ]

        payment_vals = {
            'date': self.date,
            'memo': self.name,
            'journal_id': self.journal_id.id,
            'amount': self.total_amount_currency,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': self.vendor_id.id,
            'currency_id': self.currency_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'company_id': self.company_id.id,
        }

        move_vals = {
            **self._prepare_move_vals(),
            'date': self.date or fields.Date.context_today(self),
            'ref': self.name,
            'journal_id': self.journal_id.id,
            'partner_id': self.vendor_id.id,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'line_ids': [Command.create(line) for line in move_lines],
        }

        return move_vals, payment_vals

    def _create_entry_for_expense_with_linked_bill(self):
        """
        Create different entries to:
        - transfer the debt from the vendor to the employee
        - prepare the payment to the employee
        """
        for expense in self:
            payment_move_vals, payment_vals, debt_transfer_move_vals = expense._prepare_linked_bill_paid_by_employee_payment_vals()
            # Sudoed as approvers may not be accountants, the values are built from the expense only
            payment_move_sudo, debt_transfer_move_sudo = self.env['account.move'].sudo().create([payment_move_vals, debt_transfer_move_vals])
            payment_vals['move_id'] = payment_move_sudo.id
            payment_sudo = self.env['account.payment'].sudo().create(payment_vals)
            payment_move_sudo.update({
                'origin_payment_id': payment_sudo.id,
                'journal_id': payment_move_sudo.journal_id.id,
            })
            debt_transfer_move_sudo.action_post()

            # reconcile payment move with debt transfer entry move
            payment_move_payable_lines = payment_move_sudo.line_ids.filtered(lambda l: l.account_type == 'liability_payable')
            transfer_move_payable_lines = debt_transfer_move_sudo.line_ids.filtered(
                lambda l: l.account_type == 'liability_payable' and l.partner_id == expense.employee_id.user_id.partner_id
            )
            if payment_move_payable_lines and transfer_move_payable_lines:
                (payment_move_payable_lines + transfer_move_payable_lines).reconcile()

    def _prepare_linked_bill_paid_by_employee_payment_vals(self):
        """
        Prepare the values of the different entries and payment needed for an expense paid by employee
        - 1 move for the payment -> PNBK (expense employee payment)
        - 1 payment (to set the origin_payment_id later)
        - 1 move for the debt transfer -> MISC (Debt transfer entry)
        """
        self.ensure_one()
        employee_partner = self.employee_id.user_id.partner_id

        # DEBT TRANSFER ENTRY LINES
        move_lines = [
            # Debit: The payable account (neutralizing the debt of the original bill)
            {
                'name': self._get_move_line_name(),
                'account_id': self.account_id.id,
                'expense_id': self.id,
                'amount_currency': self.total_amount_currency,
                'balance': self.total_amount,
                'currency_id': self.currency_id.id,
                'partner_id': self.vendor_id.id,
            },
            # Credit: The payable account (transfering debt to employee entry)
            {
                'name': self._get_move_line_name(),
                'account_id': self.account_id.id,
                'expense_id': self.id,
                'amount_currency': -self.total_amount_currency,
                'balance': -self.total_amount,
                'currency_id': self.currency_id.id,
                'partner_id': employee_partner.id,
            },
        ]

        # DEBT TRANSFER ENTRY
        debt_transfer_move_vals = {
            'date': self.date or fields.Date.context_today(self),
            'ref': self.name,
            'move_type': 'entry',
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'line_ids': [Command.create(line) for line in move_lines],
        }

        # PAYMENT
        payment_vals = {
            'date': self.date,
            'memo': self.name,
            'amount': self.total_amount_currency,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': employee_partner.id,
            'currency_id': self.currency_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'company_id': self.company_id.id,
        }

        # PAYMENT MOVE LINES
        payment_move_lines = [
            # Debit: the payable account
            {
                'name': self._get_move_line_name(),
                'account_id': self.account_id.id,
                'expense_id': self.id,
                'amount_currency': self.total_amount_currency,
                'balance': self.total_amount,
                'currency_id': self.currency_id.id,
                'partner_id': employee_partner.id,
            },
            # Credit: the outstanding payment account, to pay the employee
            {
                'name': self._get_move_line_name(),
                'account_id': self._get_outstanding_account_id().id,
                'amount_currency': -self.total_amount_currency,
                'balance': -self.total_amount,
                'currency_id': self.currency_id.id,
                'partner_id': employee_partner.id,
            }
        ]

        # PAYMENT MOVE
        payment_move_vals = {
            **self._prepare_move_vals(),
            'date': self.date or fields.Date.context_today(self),
            'ref': self.name,
            'move_type': 'entry',
            'partner_id': employee_partner.id,
            'journal_id': self.env['account.journal'].search(
                [('type', '=', 'bank'), ('company_id', '=', self.env.company.id)], limit=1).id,
            'commercial_partner_id': employee_partner.id,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'line_ids': [Command.create(line) for line in payment_move_lines],
            'partner_bank_id': self.employee_id.sudo().primary_bank_account_id.id,
            'attachment_ids': False,
        }

        return payment_move_vals, payment_vals, debt_transfer_move_vals

    def _prepare_move_vals(self):
        return {
            # force the name to the default value, to avoid an eventual 'default_name' in the context
            # that would set it to '' which would then cause no number to be given to the account.move
            # when it is paid.
            'name': '/',
            'expense_ids': [Command.set(self.ids)],
        }

    def _prepare_move_lines_vals(self):
        self.ensure_one()
        return {
            'name': self._get_move_line_name(),
            'account_id': self._get_base_account().id,
            'quantity': self.quantity or 1,
            'price_unit': self.price_unit,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom_id.id,
            'analytic_distribution': self.analytic_distribution,
            'expense_id': self.id,
            'partner_id': False if self.payment_mode == 'company_account' else self.employee_id.sudo().work_contact_id.id,
            'tax_ids': [Command.set(self.tax_ids.ids)],
        }

    def _prepare_base_line_for_taxes_computation(self, **kwargs):
        self.ensure_one()
        return self.env['account.tax']._prepare_base_line_for_taxes_computation(
            self,
            **{'partner_id': self.vendor_id, 'special_mode': 'total_included', 'rate': self.currency_rate, **kwargs},
        )

    def _get_move_line_name(self):
        """ Helper to get the name of the account move lines related to an expense """
        self.ensure_one()
        expense_name = self.name.split("\n")[0][:64]
        return self.env._('%(employee_name)s: %(expense_name)s', employee_name=self.employee_id.name, expense_name=expense_name)

    def _get_base_account(self):
        """
        Returns the expense account or forces default values if none was found
        We need to do this as the installation process may delete the original account, and it doesn't recompute properly after
        Returned expense accounts are the first expense account encountered in the following list:
        1. expense account of the expense itself
        2. expense account of the product
        3. expense account of the company
        4. expense account on the purchase journal for employee expense
        """

        # expense account of the expense itself
        account = self.account_id
        if account:
            return account

        # expense account of the product then the product category
        if self.product_id:
            account = self.product_id.with_company(self.company_id).product_tmpl_id._get_product_accounts()['expense']
        else:
            account = self.env.company.expense_account_id

        if account:
            return account

        # expense account on the purchase journal for employee expense
        journal = self.journal_id
        if journal.type == 'purchase':
            account = journal.default_account_id

        if not account:
            raise UserError(self.env._(
                "Odoo had a look at your expense, its product, your company and the journal but came back with empty hands.\n"
                "Give Odoo a hand to find an account by setting up an expense account.\n"
                "%(expense)s %(expense_name)s.\n",
                expense=self,
                expense_name=self.name,
            ))
        return account

    def _get_expense_account_destination(self):
        # account.move used to allow having several expenses with payment_mode = 'company_account'.
        # This method needs to support processing several expenses to allow reconciliation of old account.move.line
        ids = set()
        for expense in self:
            if expense.payment_mode == 'company_account':
                account_dest = expense.payment_method_line_id.payment_account_id or expense._get_outstanding_account_id()
            elif not expense.employee_id.sudo().work_contact_id:
                raise UserError(self.env._(
                    "No work contact found for the employee %(name)s, please configure one.",
                    name=expense.employee_id.name,
                ))
            else:
                partner = expense.employee_id.sudo().work_contact_id.with_company(expense.company_id)
                account_dest = partner.property_account_payable_id or partner.parent_id.property_account_payable_id
            ids.add(account_dest.id)

        # mimics <account.account>.id
        if not ids:
            return False
        if len(ids) > 1:
            raise UserError(self.env._(
                "The following expenses payment method leads to several accounts payable and this isn't supported:\n%(expenses)s",
                expenses=self.browse(ids),
            ))
        return ids.pop()

    def _get_outstanding_account_id(self):
        account_ref = 'account_journal_payment_debit_account_id' if self.payment_method_line_id.payment_type == 'inbound' else 'account_journal_payment_credit_account_id'
        chart_template = self.with_context(allowed_company_ids=self.company_id.root_id.ids).env['account.chart.template']
        outstanding_account = chart_template.ref(account_ref, raise_if_not_found=False)
        if not outstanding_account:
            bank_prefix = self.company_id.bank_account_code_prefix
            first_account = self.env['account.account'].search([('company_ids', 'in', self.company_id.id)], limit=1)
            code_digits = len(first_account.code or '') or 6
            chart_template._create_outstanding_accounts(self.company_id, bank_prefix, code_digits)
            outstanding_account = chart_template.ref(account_ref, raise_if_not_found=False)
        if not outstanding_account.active:
            raise RedirectWarning(
                message=self.env._("The account %(name)s (%(code)s) is archived. Activate it to continue", name=outstanding_account.name, code=outstanding_account.code),
                action=outstanding_account._get_records_action(),
                button_text=self.env._("Go to Account"),
            )
        return outstanding_account

    def _get_default_journal(self):
        """
        Get default journal for expenses paid by employee
        """
        self.ensure_one()
        closest_company_journal = self.company_id.expense_journal_id or self.company_id.parent_ids[::-1].expense_journal_id[:1]
        if closest_company_journal:
            return closest_company_journal
        return self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(self.company_id.id),
            ('type', '=', 'purchase'),
        ], limit=1)

    def _creation_message(self):
        if self.env.context.get('from_split_wizard'):
            return self.env._("Expense created from a split.")
        return super()._creation_message()
