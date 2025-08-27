# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from markupsafe import Markup
import logging
import werkzeug

from odoo import api, fields, Command, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools import clean_context, email_normalize, float_repr, float_round, format_date, is_html_empty


_logger = logging.getLogger(__name__)

EXPENSE_APPROVAL_STATE = [
    ('submitted', 'Submitted'),
    ('approved', 'Approved'),
    ('refused', 'Refused'),
]


class HrExpense(models.Model):
    """
        Here are the rights associated with the expense flow

        Action       Group                   Restriction
        =================================================================================
        Submit      Employee                Only his own
                    Officer                 If he is expense manager of the employee, manager of the employee
                                              or the employee is in the department managed by the officer
                    Manager                 Always
        Approve     Officer                 Not his own and he is expense manager of the employee, manager of the employee
                                              or the employee is in the department managed by the officer
                    Manager                 Always
        Post        Billing accountant      State == approved
        Cancel      Officer                 Not his own and he is expense manager of the employee, manager of the employee
                                              or the employee is in the department managed by the officer
                    Manager                 Always
        =================================================================================
    """
    _name = 'hr.expense'
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin', 'analytic.mixin']
    _description = "Expense"
    _order = "date desc, id desc"
    _check_company_auto = True

    @api.model
    def _default_employee_id(self):
        employee = self.env.user.employee_id
        if not employee and not self.env.user.has_group('hr_expense.group_hr_expense_team_approver'):
            raise ValidationError(_('The current user has no related employee. Please, create one.'))
        return employee

    name = fields.Char(
        string="Description",
        compute='_compute_name', precompute=True, store=True, readonly=False,
        required=True,
        copy=True,
    )
    date = fields.Date(string="Expense Date", default=fields.Date.context_today)
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string="Employee",
        compute='_compute_employee_id', precompute=True, store=True, readonly=False,
        required=True,
        default=_default_employee_id,
        check_company=True,
        domain=[('filter_for_expense', '=', True)],
        tracking=True,
    )
    department_id = fields.Many2one(
        comodel_name='hr.department',
        string="Department",
        compute='_compute_from_employee_id', store=True,
        copy=False,
    )
    manager_id = fields.Many2one(
        comodel_name='res.users',
        string="Manager",
        compute='_compute_from_employee_id', store=True,
        domain=lambda self: [('share', '=', False), '|', ('employee_id.expense_manager_id', 'in', self.env.user.id), ('all_group_ids', 'in', self.env.ref('hr_expense.group_hr_expense_team_approver').ids)],
        copy=False,
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    # product_id is not required to allow to create an expense without product via mail alias, but should be required on the view.
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Category",
        tracking=True,
        check_company=True,
        domain=[('can_be_expensed', '=', True)],
        ondelete='restrict',
    )
    product_description = fields.Html(compute='_compute_product_description')
    product_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string="Unit",
        compute='_compute_uom_id', precompute=True, store=True,
        copy=True,
    )
    product_has_cost = fields.Boolean(compute='_compute_from_product')  # Whether the product has a cost (standard_price) or not
    product_has_tax = fields.Boolean(string="Whether tax is defined on a selected product", compute='_compute_from_product')
    quantity = fields.Float(required=True, digits='Product Unit', default=1)
    description = fields.Text(string="Internal Notes")
    message_main_attachment_checksum = fields.Char(related='message_main_attachment_id.checksum')
    nb_attachment = fields.Integer(string="Number of Attachments", compute='_compute_nb_attachment')
    attachment_ids = fields.One2many(
        comodel_name='ir.attachment',
        inverse_name='res_id',
        domain=[('res_model', '=', 'hr.expense')],
        string="Attachments",
    )
    state = fields.Selection(
        selection=[
            # Pre-Approval states
            ('draft', 'Draft'),
            # Approval states
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('posted', 'Posted'),
            # Payment states
            ('in_payment', 'In Payment'),
            ('paid', 'Paid'),
            # refused state is always last
            ('refused', 'Refused'),
        ],
        string="Status",
        compute='_compute_state', store=True, readonly=True,
        index=True,
        copy=False,
        default='draft',
        tracking=True,
    )
    approval_state = fields.Selection(selection=EXPENSE_APPROVAL_STATE, copy=False, readonly=True)
    approval_date = fields.Datetime(string="Approval Date", readonly=True)
    duplicate_expense_ids = fields.Many2many(comodel_name='hr.expense', compute='_compute_duplicate_expense_ids')  # Used to trigger warnings
    same_receipt_expense_ids = fields.Many2many(comodel_name='hr.expense', compute='_compute_same_receipt_expense_ids')  # Used to trigger warnings

    split_expense_origin_id = fields.Many2one(
        comodel_name='hr.expense',
        string="Origin Split Expense",
        help="Original expense from a split.",
    )
    # Amount fields
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
    total_amount_currency = fields.Monetary(
        string="Total In Currency",
        currency_field='currency_id',
        compute='_compute_total_amount_currency', precompute=True, store=True, readonly=False,
        tracking=True,
    )
    total_amount = fields.Monetary(
        string="Total",
        currency_field='company_currency_id',
        compute='_compute_total_amount', inverse='_inverse_total_amount', precompute=True, store=True, readonly=False,
        tracking=True,
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
    price_unit = fields.Float(
        string="Unit Price",
        compute='_compute_price_unit', precompute=True, store=True, required=True, readonly=True,
        copy=True,
        digits='Product Price',
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string="Currency",
        compute='_compute_currency_id', precompute=True, store=True, readonly=False,
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='company_id.currency_id',
        string="Report Company Currency",
        readonly=True,
    )
    is_multiple_currency = fields.Boolean(
        string="Is currency_id different from the company_currency_id",
        compute='_compute_is_multiple_currency',
    )
    currency_rate = fields.Float(compute='_compute_currency_rate', digits=(16, 9), readonly=True, tracking=True)
    label_currency_rate = fields.Char(compute='_compute_currency_rate', readonly=True)

    # Account fields
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        related='payment_method_line_id.journal_id',
        readonly=True,
    )
    selectable_payment_method_line_ids = fields.Many2many(
        comodel_name='account.payment.method.line',
        compute='_compute_selectable_payment_method_line_ids',
    )
    payment_method_line_id = fields.Many2one(
        comodel_name='account.payment.method.line',
        string="Payment Method",
        compute='_compute_payment_method_line_id', store=True, readonly=False,
        domain="[('id', 'in', selectable_payment_method_line_ids)]",
        help="The payment method used when the expense is paid by the company.",
    )
    account_move_id = fields.Many2one(
        string="Journal Entry",
        comodel_name='account.move',
        readonly=True,
        copy=False,
        index='btree_not_null',
    )
    payment_mode = fields.Selection(
        selection=[
            ('own_account', "Employee (to reimburse)"),
            ('company_account', "Company")
        ],
        string="Paid By",
        default='own_account',
        required=True,
        tracking=True,
    )
    vendor_id = fields.Many2one(comodel_name='res.partner', string="Vendor")
    account_id = fields.Many2one(
        comodel_name='account.account',
        string="Account",
        compute='_compute_account_id', precompute=True, store=True, readonly=False,
        check_company=True,
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card'))]",
        help="An expense account is expected",
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
    is_editable = fields.Boolean(string="Is Editable By Current User", compute='_compute_is_editable', readonly=True)
    can_reset = fields.Boolean(string='Can Reset', compute='_compute_can_reset', readonly=True)
    can_approve = fields.Boolean(string='Can Approve', compute='_compute_can_approve', readonly=True)

    # Legacy sheet field, allow grouping of expenses to keep the grouping mechanic data and allow it to be re-used when re-implemented
    former_sheet_id = fields.Integer(string='Former Report')

    # --------------------------------------------
    # Constraints
    # --------------------------------------------

    @api.constrains('state', 'approval_state', 'total_amount', 'total_amount_currency')
    def _check_non_zero(self):
        """ Helper to raise when we should ensure that an expense isn't approved  """
        for expense in self:
            total_amount_is_zero = expense.company_currency_id.is_zero(expense.total_amount)
            total_amount_currency_is_zero = expense.currency_id.is_zero(expense.total_amount_currency)
            if (expense.state != 'draft' or expense.approval_state != False) and (total_amount_is_zero or total_amount_currency_is_zero):
                raise ValidationError(_("Only draft expenses can have a total of 0."))

    @api.constrains('account_move_id')
    def _check_o2o_payment(self):
        for expense in self:
            if len(expense.account_move_id.origin_payment_id.expense_ids) > 1:
                raise ValidationError(_("Only one expense can be linked to a particular payment"))

    # --------------------------------------------
    # Compute methods
    # --------------------------------------------

    @api.depends('product_has_cost')
    def _compute_currency_id(self):
        for expense in self:
            if expense.product_has_cost and expense.state == 'draft':
                expense.currency_id = expense.company_currency_id

    @api.depends_context('uid')
    @api.depends('employee_id', 'manager_id', 'state')
    def _compute_is_editable(self):
        is_hr_admin = (
            self.env.user.has_group('hr_expense.group_hr_expense_manager')
            or self.env.su
        )
        is_team_approver = self.env.user.has_group('hr_expense.group_hr_expense_team_approver')
        is_all_approver = self.env.user.has_group('hr_expense.group_hr_expense_user')

        expenses_employee_ids_under_user_ones = set()
        if is_team_approver:
            expenses_employee_ids_under_user_ones = set(
                self.env['hr.employee'].sudo().search(
                    [
                        ('id', 'in', self.employee_id.ids),
                        ('id', 'child_of', self.env.user.employee_ids.ids),
                        ('id', 'not in', self.env.user.employee_ids.ids),
                    ]
                ).ids
            )
        for expense in self:
            if not expense.company_id:
                # This would be happening when emptying the required company_id field, triggering the "onchange"s.
                # This would lead to fields being set as editable, instead of using the env company,
                # recomputing the interface just to be blocked when trying to save we choose not to recompute anything
                # and wait for a proper company to be inputted.
                continue
            if expense.state not in {'draft', 'submitted', 'approved'} and not self.env.su:
                # Not editable
                expense.is_editable = False
                continue

            if is_hr_admin:
                # Administrator-level users are not restricted, they can edit their own expenses
                expense.is_editable = True
                continue

            employee = expense.employee_id
            is_own_expense = employee.user_id == self.env.user
            if is_own_expense and expense.state == 'draft':
                # Anyone can edit their own draft expense
                expense.is_editable = True
                continue

            managers = (
                expense.manager_id
                | employee.expense_manager_id
                | employee.sudo().department_id.manager_id.user_id.sudo(self.env.su)
            )
            if is_all_approver:
                managers |= self.env.user
            if expense.employee_id.id in expenses_employee_ids_under_user_ones:
                    managers |= self.env.user
            if not is_own_expense and self.env.user in managers:
                # If Approver-level or designated manager, can edit other people expense
                expense.is_editable = True
                continue
            expense.is_editable = False

    @api.onchange('product_has_cost')
    def _onchange_product_has_cost(self):
        """ Reset quantity to 1, in case of 0-cost product. To make sure switching non-0-cost to 0-cost doesn't keep the quantity."""
        if not self.product_has_cost and self.state == 'draft':
            self.quantity = 1

    @api.depends_context('lang')
    @api.depends('product_id')
    def _compute_product_description(self):
        for expense in self:
            expense.product_description = not is_html_empty(expense.product_id.description) and expense.product_id.description

    @api.depends('product_id')
    def _compute_name(self):
        for expense in self:
            expense.name = expense.name or expense.product_id.display_name

    def _set_expense_currency_rate(self, date_today):
        for expense in self:
            company_currency = expense.company_currency_id or self.env.company.currency_id
            expense.currency_rate = expense.env['res.currency']._get_conversion_rate(
                from_currency=expense.currency_id or company_currency,
                to_currency=company_currency,
                company=expense.company_id,
                date=expense.date or date_today,
            )

    @api.depends('currency_id', 'total_amount_currency', 'date')
    def _compute_currency_rate(self):
        """
            We want the default odoo rate when the following change:
            - the currency of the expense
            - the total amount in foreign currency
            - the date of the expense
            this will cause the rate to be recomputed twice with possible changes but we don't have the required fields
            to store the override state in stable
        """
        date_today = fields.Date.context_today(self)
        for expense in self:
            if expense.is_multiple_currency:
                if (
                        expense.currency_id != expense._origin.currency_id
                        or expense.total_amount_currency != expense._origin.total_amount_currency
                        or expense.date != expense._origin.date
                ):
                    expense._set_expense_currency_rate(date_today=date_today)
                else:
                    expense.currency_rate = expense.total_amount / expense.total_amount_currency if expense.total_amount_currency else 1.0
            else:  # Mono-currency case computation shortcut, no need for the label if there is no conversion
                expense.currency_rate = 1.0
                expense.label_currency_rate = False
                continue

            company_currency = expense.company_currency_id or expense.env.company.currency_id
            expense.label_currency_rate = _(
                '1 %(exp_cur)s = %(rate)s %(comp_cur)s',
                exp_cur=(expense.currency_id or company_currency).name,
                rate=float_repr(expense.currency_rate, 6),
                comp_cur=company_currency.name,
            )

    @api.depends('currency_id', 'company_currency_id')
    def _compute_is_multiple_currency(self):
        for expense in self:
            expense_currency = expense.currency_id or expense.company_currency_id or expense.env.company.currency_id
            expense_company_currency = expense.company_currency_id or expense.env.company.currency_id
            expense.is_multiple_currency = expense_currency != expense_company_currency

    @api.depends('product_id')
    def _compute_from_product(self):
        for expense in self:
            expense.product_has_cost = expense.product_id and not expense.company_currency_id.is_zero(expense.product_id.standard_price)
            expense.product_has_tax = bool(expense.product_id.supplier_taxes_id.filtered_domain(self.env['account.tax']._check_company_domain(expense.company_id)))

    @api.depends('product_id.uom_id')
    def _compute_uom_id(self):
        for expense in self:
            expense.product_uom_id = expense.product_id.uom_id

    @api.depends('amount_residual', 'account_move_id.state', 'account_move_id.payment_state', 'approval_state')
    def _compute_state(self):
        """
        Compute the states of the expense as such (priority is given to the last matching state of the list):
            - draft: By default
            - submitted: When the approval_state is 'submitted'
            - approved: When the approval_state is 'approved'
            - refused: When the approval_state is 'refused'
            - paid: When it is a company paid expense or the move state is neither 'draft' nor 'posted'
            - in_payment (or paid): When the move state is 'posted' and it's 'payment_state' is 'in_payment' or 'paid'
                                    or ('partial' and there is a residual amount)
            - posted: When the linked move state is 'draft', or if it is 'posted' and it's 'payment_state' is 'not_paid'
        """
        for expense in self:
            move = expense.account_move_id
            if move.state == 'cancel':
                expense.state = 'paid'
                continue
            if move:
                if expense.payment_mode == 'company_account':
                    # Shortcut to paid, as it's already paid, but we may not have the bank statement yet
                    expense.state = 'paid'
                elif move.state == 'draft':
                    expense.state = 'posted'
                elif move.payment_state == 'not_paid':
                    expense.state = 'posted'
                elif (
                        move.payment_state == 'in_payment'
                        or (move.payment_state == 'partial' and not expense.company_currency_id.is_zero(expense.amount_residual))
                ):
                    expense.state = self.env['account.move']._get_invoice_in_payment_state()
                else:  # Partial, reversed or in_payment
                    expense.state = 'paid'
                continue
            expense.state = expense.approval_state or 'draft'

    @api.depends('employee_id', 'employee_id.department_id')
    def _compute_from_employee_id(self):
        for expense in self:
            expense.department_id = expense.employee_id.department_id
            expense.manager_id = expense._get_default_responsible_for_approval()

    @api.depends('quantity', 'price_unit', 'tax_ids')
    def _compute_total_amount_currency(self):
        AccountTax = self.env['account.tax']
        for expense in self.filtered('product_has_cost'):
            base_line = expense._prepare_base_line_for_taxes_computation(price_unit=expense.price_unit, quantity=expense.quantity)
            AccountTax._add_tax_details_in_base_line(base_line, expense.company_id)
            AccountTax._round_base_lines_tax_details([base_line], expense.company_id)
            expense.total_amount_currency = base_line['tax_details']['total_included_currency']

    @api.onchange('total_amount_currency')
    def _inverse_total_amount_currency(self):
        for expense in self:
            if not expense.is_editable:
                raise UserError(_(
                    "Uh-oh! You can’t edit this expense.\n\n"
                    "Reach out to the administrators, flash your best smile, and see if they'll grant you the magical access you seek."
                ))
            expense.price_unit = (expense.total_amount / expense.quantity) if expense.quantity != 0 else 0.

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
        """ Allows to set a custom rate on the expense, and avoid the override when it makes no sense """
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
                expense.untaxed_amount =  tax_details['total_excluded_currency']
            else:
                expense.total_amount_currency = expense.total_amount
                expense.tax_amount = expense.tax_amount_currency
                expense.untaxed_amount = expense.untaxed_amount_currency
            expense.currency_rate = expense.total_amount / expense.total_amount_currency if expense.total_amount_currency else 1.0
            expense.price_unit = expense.total_amount / expense.quantity if expense.quantity else expense.total_amount

    @api.depends('product_id', 'company_id')
    def _compute_tax_ids(self):
        for _expense in self.filtered('company_id'):   # Avoid a traceback, the field is required anyway
            expense = _expense.with_company(_expense.company_id)
            # taxes only from the same company
            expense.tax_ids = expense.product_id.supplier_taxes_id.filtered_domain(self.env['account.tax']._check_company_domain(expense.company_id))

    @api.depends('total_amount_currency', 'tax_ids')
    def _compute_tax_amount_currency(self):
        """
             Note: as total_amount_currency can be set directly by the user (for product without cost)
             or needs to be computed (for product with cost), `untaxed_amount_currency` can't be computed in the same method as `total_amount_currency`.
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

    @api.depends('total_amount', 'total_amount_currency')
    def _compute_price_unit(self):
        """
           The price_unit is the unit price of the product if no product is set and no attachment overrides it.
           Otherwise it is always computed from the total_amount and the quantity else it would break the Receipt Entry
           when edited after creation.
        """
        for expense in self:
            if expense.state != 'draft':
                continue

            if not expense.company_id:
                # This would be happening when emptying the required company_id field, triggering the "onchange"s.
                # A traceback would occur because company_currency_id would be set to False.
                # Instead of using the env company, recomputing the interface just to be blocked when trying to save
                # we choose not to recompute anything and wait for a proper company to be inputted.
                continue

            product_id = expense.product_id
            if expense._needs_product_price_computation():
                expense.price_unit = product_id._price_compute(
                    'standard_price',
                    uom=expense.product_uom_id,
                    company=expense.company_id,
                )[product_id.id]
            else:
                expense.price_unit = expense.company_currency_id.round(expense.total_amount / expense.quantity) if expense.quantity else 0.

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
                ])

    @api.depends('product_id', 'company_id')
    def _compute_account_id(self):
        for _expense in self:
            expense = _expense.with_company(_expense.company_id)
            if not expense.product_id:
                expense.account_id = _expense.company_id.expense_account_id
                continue
            account = expense.product_id.product_tmpl_id._get_product_accounts()['expense']
            if account:
                expense.account_id = account

    @api.depends('company_id')
    def _compute_employee_id(self):
        if not self.env.context.get('default_employee_id'):
            for expense in self:
                expense.employee_id = self.env.user.with_company(expense.company_id).employee_id

    @api.depends('attachment_ids')
    def _compute_same_receipt_expense_ids(self):
        self.same_receipt_expense_ids = [Command.clear()]

        expenses_with_attachments = self.filtered(lambda expense: expense.attachment_ids and not expense.split_expense_origin_id)
        if not expenses_with_attachments:
            return

        expenses_groupby_checksum = dict(self.env['ir.attachment']._read_group(domain=[
            ('res_model', '=', 'hr.expense'),
            ('checksum', 'in', expenses_with_attachments.attachment_ids.mapped('checksum'))],
            groupby=['checksum'],
            aggregates=['res_id:array_agg'],
        ))

        for expense in expenses_with_attachments:
            same_receipt_ids = set()
            for attachment in expense.attachment_ids:
                same_receipt_ids.update(expenses_groupby_checksum[attachment.checksum])
            same_receipt_ids.remove(expense.id)

            expense.same_receipt_expense_ids = [Command.set(list(same_receipt_ids))]

    @api.depends('employee_id', 'product_id', 'total_amount_currency')
    def _compute_duplicate_expense_ids(self):
        self.duplicate_expense_ids = [Command.clear()]

        expenses = self.filtered(lambda expense: expense.employee_id and expense.product_id and expense.total_amount_currency)
        if expenses.ids:
            duplicates_query = """
              SELECT ARRAY_AGG(DISTINCT he.id)
                FROM hr_expense AS he
                JOIN hr_expense AS ex ON he.employee_id = ex.employee_id
                                     AND he.product_id = ex.product_id
                                     AND he.date = ex.date
                                     AND he.total_amount_currency = ex.total_amount_currency
                                     AND he.company_id = ex.company_id
                                     AND he.currency_id = ex.currency_id
               WHERE ex.id in %(expense_ids)s
               GROUP BY he.employee_id, he.product_id, he.date, he.total_amount_currency, he.company_id, he.currency_id
              HAVING COUNT(he.id) > 1
            """
            self.env.cr.execute(duplicates_query, {'expense_ids': tuple(expenses.ids)})

            for duplicates_ids in (x[0] for x in self.env.cr.fetchall()):
                expenses_duplicates = expenses.filtered(lambda expense: expense.id in duplicates_ids)
                expenses_duplicates.duplicate_expense_ids = [Command.set(duplicates_ids)]
                expenses = expenses - expenses_duplicates

    @api.depends('product_id', 'account_id', 'employee_id')
    def _compute_analytic_distribution(self):
        for expense in self:
            distribution = self.env['account.analytic.distribution.model']._get_distribution({
                'product_id': expense.product_id.id,
                'product_categ_id': expense.product_id.categ_id.id,
                'partner_id': expense.employee_id.work_contact_id.id,
                'partner_category_id': expense.employee_id.work_contact_id.category_id.ids,
                'account_prefix': expense.account_id.code,
                'company_id': expense.company_id.id,
            })
            expense.analytic_distribution = distribution or expense.analytic_distribution

    def _compute_nb_attachment(self):
        attachment_data = self.env['ir.attachment']._read_group(
            [('res_model', '=', 'hr.expense'), ('res_id', 'in', self.ids)],
            ['res_id'],
            ['__count'],
        )
        attachment = dict(attachment_data)
        for expense in self:
            expense.nb_attachment = attachment.get(expense._origin.id, 0)

    @api.depends_context('uid')
    @api.depends('employee_id', 'state')
    def _compute_can_reset(self):
        user = self.env.user
        is_team_approver = user.has_group('hr_expense.group_hr_expense_team_approver') or self.env.su
        is_all_approver = user.has_groups('hr_expense.group_hr_expense_user,hr_expense.group_hr_expense_manager') or self.env.su

        valid_company_ids = set(self.env.companies.ids)
        expenses_employee_ids_under_user_ones = set()
        if is_team_approver:  # We don't need to search if the user has not the required rights
            expenses_employee_ids_under_user_ones = set(self.env['hr.employee'].sudo().search([
                ('id', 'in', self.employee_id.ids),
                ('id', 'child_of', user.employee_ids.ids),
                ('id', 'not in', user.employee_ids.ids),
            ]).ids)

        for expense in self:
            expense.can_reset = (
                expense.company_id.id in valid_company_ids
                and (
                        is_all_approver
                        or expense.employee_id.id in expenses_employee_ids_under_user_ones
                        or expense.employee_id.expense_manager_id == user
                        or (expense.state in {'draft', 'submitted'} and expense.employee_id.user_id == user)
                )
            )

    @api.depends_context('uid')
    @api.depends('employee_id')
    def _compute_can_approve(self):
        cannot_reason_per_record_id = self._get_cannot_approve_reason()
        for expense in self:
            expense.can_approve = not cannot_reason_per_record_id[expense.id]

    # ----------------------------------------
    # ORM Overrides
    # ----------------------------------------

    @api.ondelete(at_uninstall=False)
    def _unlink_except_approved(self):
        for expense in self:
            if expense.state in {'approved', 'posted', 'in_payment', 'paid'}:
                raise UserError(_('You cannot delete a posted or approved expense.'))

    def write(self, vals):
        if any(field in vals for field in {'is_editable', 'can_approve', 'can_refuse'}):
            raise UserError(_("You cannot edit the security fields of an expense manually"))

        if any(field in vals for field in {'tax_ids', 'analytic_distribution', 'account_id', 'manager_id'}):
            if any((not expense.is_editable and not self.env.su) for expense in self):
                raise UserError(_(
                    "Uh-oh! You can’t edit this expense.\n\n"
                    "Reach out to the administrators, flash your best smile, and see if they'll grant you the magical access you seek."
                ))

        res = super().write(vals)

        if vals.get('state') == 'approved' or vals.get('approval_state') == 'approved':
            self._check_can_approve()
        elif vals.get('state') == 'refused' or vals.get('approval_state') == 'refused':
            self._check_can_refuse()

        if 'currency_id' in vals:
            self._set_expense_currency_rate(date_today=fields.Date.context_today(self))
            for expense in self:
                expense.total_amount = expense.total_amount_currency * expense.currency_rate
        return res

    @api.model_create_multi
    def create(self, vals_list):
        expenses = super().create(vals_list)
        expenses.update_activities_and_mails()
        return expenses

    # --------------------------------------------
    # Mail Thread
    # --------------------------------------------

    def _message_auto_subscribe_followers(self, updated_values, subtype_ids):
        res = super()._message_auto_subscribe_followers(updated_values, subtype_ids)
        if updated_values.get('employee_id'):
            employee_user = self.env['hr.employee'].browse(updated_values['employee_id']).user_id
            if employee_user:
                res.append((employee_user.partner_id.id, subtype_ids, False))
        return res

    @api.model
    def _get_employee_from_email(self, email_address):
        if not email_address:
            return self.env['hr.employee']
        employee = self.env['hr.employee'].search([
            ('user_id', '!=', False), '|', ('work_email', 'ilike', email_address), ('user_id.email', 'ilike', email_address),
        ])

        if len(employee) > 1:
            # Several employees can be linked to the same user.
            # In that case, we only keep the employee that matched the user's company.
            return employee.filtered(lambda e: e.company_id == e.user_id.company_id)

        if not employee:
            # An employee does not always have a user.
            return self.env['hr.employee'].search([
                ('user_id', '=', False),
                ('work_email', 'ilike', email_address),
            ], limit=1)

        return employee

    @api.model
    def _parse_product(self, expense_description):
        """
            Parse the subject to find the product.
            Product code should be the first word of expense_description
            Return product.product and updated description
        """
        product_code = expense_description.split(' ')[0]
        product = self.env['product.product'].search([('can_be_expensed', '=', True), ('default_code', '=ilike', product_code)], limit=1)
        if product:
            expense_description = expense_description.replace(product_code, '', 1)

        return product, expense_description

    @api.model
    def _parse_price(self, expense_description, currencies):
        """ Return price, currency and updated description """
        symbols, symbols_pattern, float_pattern = [], '', r'[+-]?(\d+[.,]?\d*)'
        price = 0.0
        for currency in currencies:
            symbols += [re.escape(currency.symbol), re.escape(currency.name)]
        symbols_pattern = '|'.join(symbols)
        price_pattern = f'(({symbols_pattern})?\\s?{float_pattern}\\s?({symbols_pattern})?)'
        matches = re.findall(price_pattern, expense_description)
        currency = currencies[:1]
        if matches:
            match = max(matches, key=lambda match: len([group for group in match if group]))
            # get the longest match. e.g. "2 chairs 120$" -> the price is 120$, not 2
            full_str = match[0]
            currency_str = match[1] or match[3]
            price = match[2].replace(',', '.')

            if currency_str and currencies:
                currencies = currencies.filtered(lambda c: currency_str in [c.symbol, c.name])
                currency = currencies[:1] or currency
            expense_description = expense_description.replace(full_str, ' ')  # remove price from description
            expense_description = re.sub(' +', ' ', expense_description.strip())

        return float(price), currency, expense_description

    @api.model
    def _parse_expense_subject(self, expense_description, currencies):
        """
            Fetch product, price and currency info from mail subject.

            Product can be identified based on product name or product code.
            It can be passed between [] or it can be placed at start.

            When parsing, only consider currencies passed as parameter.
            This will fetch currency in symbol($) or ISO name (USD).

            Some valid examples:
                Travel by Air [TICKET] USD 1205.91
                TICKET $1205.91 Travel by Air
                Extra expenses 29.10EUR [EXTRA]
        """
        product, expense_description = self._parse_product(expense_description)
        price, currency_id, expense_description = self._parse_price(expense_description, currencies)

        return product, price, currency_id, expense_description

    def _send_expense_success_mail(self, msg_dict, expense):
        """ Send a confirmation mail to the employee that an expense has been created by their previous mail """
        if expense.employee_id.user_id:
            mail_template_id = 'hr_expense.hr_expense_template_register'
        else:
            mail_template_id = 'hr_expense.hr_expense_template_register_no_user'
        rendered_body = self.env['ir.qweb']._render(mail_template_id, {'expense': expense})
        body = self.env['mail.render.mixin']._replace_local_links(rendered_body)
        if expense.employee_id.user_id.partner_id:
            expense.message_post(
                body=body,
                email_layout_xmlid='mail.mail_notification_light',
                partner_ids=expense.employee_id.user_id.partner_id.ids,
                subject=f'Re: {msg_dict.get("subject", "")}',
                subtype_xmlid='mail.mt_note',
            )
        else:
            self.env['mail.mail'].sudo().create({
                'author_id': self.env.user.partner_id.id,
                'auto_delete': True,
                'body_html': body,
                'email_from': self.env.user.email_formatted,
                'email_to': msg_dict.get('email_from', False),
                'references': msg_dict.get('message_id'),
                'subject': f'Re: {msg_dict.get("subject", "")}',
            }).send()

    @api.model
    def _get_empty_list_mail_alias(self):
        use_mailgateway = self.env['ir.config_parameter'].sudo().get_param('hr_expense.use_mailgateway')
        expense_alias = self.env.ref('hr_expense.mail_alias_expense', raise_if_not_found=False) if use_mailgateway else False
        if expense_alias and expense_alias.alias_domain and expense_alias.alias_name:
            # encode, but force %20 encoding for space instead of a + (URL / mailto difference)
            params = werkzeug.urls.url_encode({'subject': _("Lunch with customer $12.32")}).replace('+', '%20')
            return Markup(
                """<div class="text-muted mt-4">%(send_string)s <a class="text-body" href="mailto:%(alias_email)s?%(params)s">%(alias_email)s</a></div>"""
            ) % {
                'alias_email': expense_alias.display_name,
                'params': params,
                'send_string': _("Tip: try sending receipts by email"),
            }
        return ""

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' not in init_values:
            return super()._track_subtype(init_values)

        match self.state:
            case 'draft':
                return self.env.ref('hr_expense.mt_expense_reset')
            case 'cancel':
                return self.env.ref('hr_expense.mt_expense_refused')
            case 'paid':
                return self.env.ref('hr_expense.mt_expense_paid')
            case 'approved':
                if init_values['state'] in {'posted', 'in_payment', 'paid'}:  # Reverting state
                    subtype = 'hr_expense.mt_expense_entry_draft' if self.account_move_id else 'hr_expense.mt_expense_entry_delete'
                    return self.env.ref(subtype)
                return self.env.ref('hr_expense.mt_expense_approved')
            case _:
                return super()._track_subtype(init_values)

    def update_activities_and_mails(self):
        """ Update the "Review this expense" activity with the new state of the expense, also sends mail to approver to ask them to act """
        expenses_activity_done = self.env['hr.expense']
        expenses_activity_unlink = self.env['hr.expense']
        expenses_submitted_to_review = self.env['hr.expense']
        for expense in self:
            if expense.state == 'submitted':
                expense.activity_schedule(
                    'hr_expense.mail_act_expense_approval',
                    user_id=expense.manager_id.id or
                    expense.sudo()._get_default_responsible_for_approval().id or
                    self.env.user.id
                )
                expenses_submitted_to_review |= expense
            elif expense.state == 'approved':
                expenses_activity_done |= expense
            elif expense.state in {'draft', 'refused'}:
                expenses_activity_unlink |= expense

        # Batched actions
        if expenses_activity_done:
            expenses_activity_done.activity_feedback(['hr_expense.mail_act_expense_approval'])
        if expenses_activity_unlink:
            expenses_activity_unlink.activity_unlink(['hr_expense.mail_act_expense_approval'])
        # Avoid sending yourself mails
        expenses_submitted_to_review = expenses_submitted_to_review.filtered(lambda expense: expense.manager_id != self.env.user)
        if expenses_submitted_to_review:
            new_mails = []
            for company, expenses_submitted_per_company in expenses_submitted_to_review.grouped('company_id').items():
                parent_company_mails = company.parent_ids[::-1].mapped('email_formatted')
                mail_from = (
                        self.env.user.email
                        or company.email_formatted
                        or (parent_company_mails and parent_company_mails[0])
                )

                if not mail_from:  # We can't send a mail without sender
                    _logger.warning(_("Failed to send mails for submitted expenses. No valid email was found for the company"))
                    continue

                for manager, expenses_submitted in expenses_submitted_per_company.grouped('manager_id').items():
                    manager_langs = tuple(lang for lang in manager.partner_id.mapped('lang') if lang)
                    mail_lang = (manager_langs and manager_langs[0]) or self.env.lang or 'en_US'
                    body = self.env['ir.qweb']._render(
                        template='hr_expense.hr_expense_template_submitted_expenses',
                        values={'manager_name': manager.name, 'url': '/expenses-to-approve'},
                        lang=mail_lang,
                    )
                    new_mails.append({
                        'author_id': self.env.user.partner_id.id,
                        'auto_delete': True,
                        'body_html': body,
                        'email_from': mail_from,
                        'email_to': manager.employee_id.work_email or manager.email,
                        'subject': _("New expenses waiting for your approval"),
                    })
                if new_mails:
                    self.env['mail.mail'].sudo().create(new_mails).send()

    @api.model
    def get_empty_list_help(self, help_message):
        return super().get_empty_list_help((help_message or '') + self._get_empty_list_mail_alias())

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        email_address = email_normalize(msg_dict.get('email_from'))
        employee = self._get_employee_from_email(email_address)

        if not employee:
            return super().message_new(msg_dict, custom_values=custom_values)

        expense_description = msg_dict.get('subject', '')

        if employee.user_id:
            company = employee.user_id.company_id
            currencies = company.currency_id | employee.user_id.company_ids.mapped('currency_id')
        else:
            company = employee.company_id
            currencies = company.currency_id

        if not company:  # ultimate fallback, since company_id is required on expense
            company = self.env.company

        # The expenses alias is the same for all companies, we need to set the proper context
        # To select the product account
        self = self.with_company(company)

        product, price, currency_id, expense_description = self._parse_expense_subject(expense_description, currencies)
        vals = {
            'employee_id': employee.id,
            'name': expense_description,
            'total_amount_currency': price,
            'product_id': product.id if product else None,
            'product_uom_id': product.uom_id.id,
            'tax_ids': [Command.set(product.supplier_taxes_id.filtered(lambda r: r.company_id == company).ids)],
            'quantity': 1,
            'company_id': company.id,
            'currency_id': currency_id.id
        }

        account = product.product_tmpl_id._get_product_accounts()['expense']
        if account:
            vals['account_id'] = account.id

        expense = super().message_new(msg_dict, dict(custom_values or {}, **vals))
        self._send_expense_success_mail(msg_dict, expense)
        return expense

    # ----------------------------------------
    # Actions
    # ----------------------------------------

    def action_open_split_expense(self):
        self.ensure_one()
        split_expense_ids = self.search([('split_expense_origin_id', '=', self.split_expense_origin_id.id)])
        return split_expense_ids._get_records_action(name=_("Split Expenses"))

    def action_submit(self):
        """ Submit a draft expense to an approve, may skip to the approval step if no approver on the employee nor the expense """
        user = self.env.user
        for expense in self:
            if user.employee_id != expense.employee_id and not expense.can_approve:
                raise UserError(_("You do not have the required permission to submit this expense."))
            if not expense.product_id:
                raise UserError(_("You can not submit an expense without a category."))
            if not expense.manager_id:
                expense.sudo().manager_id = expense._get_default_responsible_for_approval()
        expenses_autovalidated = self.filtered(lambda expense: not expense.manager_id and not expense.employee_id.expense_manager_id)
        (self - expenses_autovalidated).approval_state = 'submitted'
        if expenses_autovalidated:  # Note, this will and should bypass the duplicate check. May be changed later
            expenses_autovalidated._do_approve(check=False)
        self.sudo().update_activities_and_mails()

    def action_approve(self):
        """ Approve an expense, pops a wizard if a duplicated expense is found to confirm they are all valid expenses """
        self._check_can_approve()
        for expense in self:
            expense._validate_distribution(
                account=expense.account_id.id,
                product=expense.product_id.id,
                business_domain='expense',
                company_id=expense.company_id.id,
            )

        duplicates = self.duplicate_expense_ids.filtered(lambda exp: exp.state in {'submitted', 'approved', 'posted', 'paid', 'in_payment'})
        if duplicates:
            action = self.env["ir.actions.act_window"]._for_xml_id('hr_expense.hr_expense_approve_duplicate_action')
            action['context'] = {'default_expense_ids': duplicates.ids}
            return action
        self._do_approve(False)

    def action_refuse(self):
        """ Refuse an expense with a reason """
        self._check_can_refuse()
        return self.env["ir.actions.act_window"]._for_xml_id('hr_expense.hr_expense_refuse_wizard_action')

    def action_post(self):
        """
        Post the expense, following one of those two options:
            - Company-paid expenses: Create and post a payment, with an accounting entry
            - Employee-paid expenses: Through a wizard, create and post a receipt
        """
        # When a move has been deleted
        self._check_can_create_move()

        company_expenses = self.filtered(lambda expense: expense.payment_mode == 'company_account')
        employee_expenses = self - company_expenses
        if len(employee_expenses.company_id) > 1:
            raise UserError(_("You can't post simultaneously employee-paid expenses belonging to different companies"))

        if company_expenses:
            company_expenses._create_company_paid_moves()
            # Post the company-paid expense through the payment, to post both at the same time
            company_expenses.account_move_id.origin_payment_id.action_post()

        if employee_expenses:
            return employee_expenses.with_context(company_paid_move_ids=company_expenses.account_move_id.ids)._post_wizard()

    def action_pay(self):
        """ Register payment shortcut on the expense form view """
        return self.account_move_id.with_context(default_partner_bank_id=(
            self.account_move_id.partner_bank_id.id if len(self.account_move_id.partner_bank_id) <= 1 else None
        )).action_register_payment()

    def action_reset(self):
        """  Reset an expense to draft state, reversing the accounting entries if needed """
        self._check_can_reset_approval()
        self = self.with_context(clean_context(self.env.context))
        moves_sudo = self.sudo().account_move_id
        draft_moves_sudo = moves_sudo.filtered(lambda m: m.state == 'draft')
        non_draft_moves_sudo = moves_sudo - draft_moves_sudo
        non_draft_moves_sudo._reverse_moves(
            default_values_list=[{'invoice_date': fields.Date.context_today(move_sudo)} for move_sudo in non_draft_moves_sudo],
            cancel=True
        )
        draft_moves_sudo.unlink()
        self._do_reset_approval()

    def attach_document(self, **kwargs):
        """When an attachment is uploaded as a receipt, set it as the main attachment."""
        self._message_set_main_attachment_id(self.env["ir.attachment"].browse(kwargs['attachment_ids'][-1:]), force=True)

    @api.model
    def _get_untitled_expense_name(self, *args):
        """ Done in a specific function to be called by hr_expense_extract to keep the same translation """
        return _("Untitled Expense %s", *args)

    @api.model
    def create_expense_from_attachments(self, attachment_ids=None, view_type='list'):
        """
            Create the expenses from files.

            :return: An action redirecting to hr.expense list view.
        """
        if not attachment_ids:
            raise UserError(_("No attachment was provided"))
        attachments = self.env['ir.attachment'].browse(attachment_ids)
        expenses = self.env['hr.expense']

        if any(attachment.res_id or attachment.res_model != 'hr.expense' for attachment in attachments):
            raise UserError(_("Invalid attachments!"))

        product = self.env['product.product'].search([('can_be_expensed', '=', True)])
        if product:
            product = product.filtered(lambda p: p.default_code == "EXP_GEN")[:1] or product[0]
        else:
            raise UserError(_("You need to have at least one category that can be expensed in your database to proceed!"))

        for attachment in attachments:
            vals = {
                'name': self._get_untitled_expense_name(format_date(self.env, fields.Date.context_today(self))),
                'price_unit': 0,
                'product_id': product.id,
            }
            if product.property_account_expense_id:
                vals['account_id'] = product.property_account_expense_id.id
            expense = self.env['hr.expense'].create(vals)
            attachment.write({'res_model': 'hr.expense', 'res_id': expense.id})

            expense._message_set_main_attachment_id(attachment, force=True)
            expenses += expense
        return expenses.ids

    def action_show_same_receipt_expense_ids(self):
        self.ensure_one()
        return self.same_receipt_expense_ids._get_records_action(
            name=_("Expenses with a similar receipt to %(other_expense_name)s", other_expense_name=self.name),
        )

    @api.model
    def get_expense_dashboard(self):
        expense_state = {
            'draft': {
                'description': _("To Submit"),
                'amount': 0.0,
                'currency': self.env.company.currency_id.id,
            },
            'submitted': {
                'description': _("Waiting Approval"),
                'amount': 0.0,
                'currency': self.env.company.currency_id.id,
            },
            'approved': {
                'description': _("Waiting Reimbursement"),
                'amount': 0.0,
                'currency': self.env.company.currency_id.id,
            }
        }
        if not self.env.user.employee_ids:
            return expense_state
        # Counting the expenses to display in the dashboard:
        # - To Submit: contains the expenses paid either by the employee or by the company, and that are draft or reported
        # - Waiting approval: contains expenses paid by the employee or paid by the company, and that have been submitted but still need to be approved/refused
        # - To be reimbursed: contains ONLY expenses paid by the employee that are approved, the payment has not yet been made
        fetched_expenses = self._read_group(
            [
                ('employee_id', 'in', self.env.user.employee_ids.ids),
                '|', ('state', 'in', ('draft', 'submitted')),
                     '&', ('payment_mode', '=', 'own_account'), ('state', '=', 'approved')
            ], ['state'], ['total_amount:sum'])
        for state, total_amount_sum in fetched_expenses:
            expense_state[state]['amount'] += total_amount_sum
        return expense_state

    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window']._for_xml_id('base.action_attachment')
        res.update({
            'domain': [('res_model', '=', 'hr.expense'), ('res_id', 'in', self.ids)],
            'context': {'default_res_model': 'hr.expense', 'default_res_id': self.id},
        })
        return res

    def action_approve_duplicates(self):
        root = self.env['ir.model.data']._xmlid_to_res_id("base.partner_root")
        for expense in self.duplicate_expense_ids:
            expense.message_post(
                body=_('%(user)s confirms this expense is not a duplicate with similar expense.', user=self.env.user.name),
                author_id=root,
            )

    def action_split_wizard(self):
        self.ensure_one()
        if self.filtered(lambda expense: expense.state in {'posted', 'paid', 'in_payment'}):
            raise UserError(_("You cannot split an expense that is already posted."))
        if not self.is_editable:
            raise UserError(_("You do not have the rights to edit this expense."))

        splits = self.env['hr.expense.split'].create(self._get_split_values())

        wizard = self.env['hr.expense.split.wizard'].create([{
            'expense_split_line_ids': splits.ids,
            'expense_id': self.id,
        }])
        return {
            'name': _("Expense split"),
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
        if self.payment_mode == 'own_account':
            res_model = 'account.move'
            record_id = self.account_move_id
        else:
            res_model = 'account.payment'
            record_id = self.account_move_id.origin_payment_id

        return {
            'type': 'ir.actions.act_window',
            'res_model': res_model,
            'name': record_id.name,
            'view_mode': 'form',
            'res_id': record_id.id,
            'views': [(False, 'form')],
        }

    # ----------------------------------------
    # Business
    # ----------------------------------------

    def _check_can_approve(self):
        if not all(self.mapped('can_approve')):
            reasons_list = tuple(reason for reason in self._get_cannot_approve_reason().values() if reason)
            reasons = _("You cannot approve:\n %(reasons)s", reasons="\n".join(reasons_list))
            raise UserError(reasons)

    def _get_cannot_approve_reason(self):
        """ Returns the reason why the user cannot approve the expense """
        is_team_approver = self.env.user.has_group('hr_expense.group_hr_expense_team_approver') or self.env.su
        is_approver = self.env.user.has_group('hr_expense.group_hr_expense_user') or self.env.su
        is_hr_admin = self.env.user.has_group('hr_expense.group_hr_expense_manager') or self.env.su

        valid_company_ids = set(self.env.companies.ids)

        expenses_employee_ids_under_user_ones = set()
        if is_team_approver:  # We don't need to search if the user has not the required rights
            expenses_employee_ids_under_user_ones = set(
                self.env['hr.employee'].sudo().search([
                    ('id', 'in', self.employee_id.ids),
                    ('id', 'child_of', self.env.user.employee_ids.ids),
                    ('id', 'not in', self.env.user.employee_ids.ids),
                ]).ids
            )
        reasons_per_record_id = {}
        for expense in self:
            reason = False
            expense_employee = expense.employee_id
            is_expense_team_approver = (
                    is_team_approver  # Admins are team approvers, not necessarily direct parents
                    or expense_employee.id in expenses_employee_ids_under_user_ones
                    or (expense_employee.expense_manager_id == self.env.user)
            )
            if expense.company_id.id not in valid_company_ids:
                reason = _(
                    "%(expense_name)s: Your are neither a Manager nor a HR Officer of this expense's company",
                    expense_name=expense.name,
                )

            elif not is_expense_team_approver:
                reason = _("%(expense_name)s: You are neither a Manager nor a HR Officer", expense_name=expense.name)

            elif not is_hr_admin:
                current_managers = (
                        expense_employee.expense_manager_id
                        | expense_employee.sudo().department_id.manager_id.user_id.sudo(self.env.su)
                        | expense.manager_id
                )
                if expense_employee.id in expenses_employee_ids_under_user_ones:
                    current_managers |= self.env.user

                if expense_employee.user_id == self.env.user:
                    reason = _("%(expense_name)s: It is your own expense", expense_name=expense.name)

                elif self.env.user not in current_managers and not is_approver:
                    reason = _("%(expense_name)s: It is not from your department", expense_name=expense.name)
            reasons_per_record_id[expense.id] = reason
        return reasons_per_record_id

    def _check_can_refuse(self):
        if not all(self.mapped('can_approve')):
            reasons = _("You cannot refuse:\n %(reasons)s", reasons="\n".join(self._get_cannot_approve_reason().values()))
            raise UserError(reasons)

    def _check_can_reset_approval(self):
        if not all(self.mapped('can_reset')):
            raise UserError(_("Only HR Officers, accountants, or the concerned employee can reset to draft."))
        if any(state not in {False, 'draft'} for state in self.account_move_id.mapped('state')):
            raise UserError(_("You cannot reset to draft an expense linked to a posted journal entry."))

    def _check_can_create_move(self):
        if any(expense.state != 'approved' for expense in self):
            raise UserError(_("You can only generate an accounting entry for approved expense(s)."))

        if False in self.mapped('payment_mode'):
            raise UserError(_("Please specify if the expenses were paid by the company, or the employee."))

    def _do_approve(self, check=True):
        if check:
            self._check_can_approve()
        expenses_to_approve = self.filtered(lambda s: s.state in {'submitted', 'draft'})
        for expense in expenses_to_approve:
            expense.write({
                'approval_state': 'approved',
                'manager_id': self.env.user.id,
                'approval_date': fields.Date.context_today(expense),
            })
        self.update_activities_and_mails()

    def _do_reset_approval(self):
        self.sudo().write({'approval_state': False, 'approval_date': False, 'account_move_id': False})
        self.update_activities_and_mails()

    def _do_refuse(self, reason):
        # Sudoed as approvers may not be accountants
        draft_moves_sudo = self.sudo().account_move_id.filtered(lambda move: move.state == 'draft')
        if self.sudo().account_move_id - draft_moves_sudo:
            raise UserError(_("You cannot cancel an expense linked to a posted journal entry"))

        if draft_moves_sudo:
            draft_moves_sudo.unlink()  # Else we have lingering moves

        self.approval_state = 'refused'
        subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment')
        for expense in self:
            expense.message_post_with_source(
                'hr_expense.hr_expense_template_refuse_reason',
                subtype_id=subtype_id,
                render_values={'reason': reason, 'name': expense.name},
            )
        self.update_activities_and_mails()

    def _get_split_values(self):
        self.ensure_one()
        half_price = self.total_amount_currency / 2
        price_round_up = float_round(half_price, precision_digits=self.currency_id.decimal_places, rounding_method='UP')
        price_round_down = float_round(half_price, precision_digits=self.currency_id.decimal_places, rounding_method='DOWN')

        return [{
            'name': self.name,
            'product_id': self.product_id.id,
            'total_amount_currency': price,
            'tax_ids': self.tax_ids.ids,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'analytic_distribution': self.analytic_distribution,
            'employee_id': self.employee_id.id,
            'approval_state': self.approval_state,
            'approval_date': self.approval_date,
            'manager_id': self.manager_id.id,
            'expense_id': self.id,
        } for price in (price_round_up, price_round_down)]

    def _get_default_responsible_for_approval(self):
        self.ensure_one()
        approver_group = 'hr_expense.group_hr_expense_team_approver'

        employee = self.employee_id.sudo()
        expense_manager = employee.expense_manager_id - employee.user_id
        if expense_manager:
            return expense_manager.sudo(False)

        department_manager = employee.department_id.manager_id.user_id - employee.user_id
        if department_manager and department_manager.has_groups(approver_group):
            return department_manager.sudo(False)

        employee_team_leader = employee.parent_id.user_id
        if employee_team_leader:
            return employee_team_leader.sudo(False)

        return self.env['res.users']

    def _needs_product_price_computation(self):
        # Hook to be overridden.
        self.ensure_one()
        return self.product_has_cost

    def _post_wizard(self):
        if 'company_account' in set(self.mapped('payment_mode')):
            raise UserError(_("Only expense paid by the employee can be posted with the wizard"))

        wizard_name = (
            _("Post expenses paid by the employee")
            if self.env.context.get('company_paid_move_ids')
            else _("Post expenses")
        )
        return {
            'type': 'ir.actions.act_window',
            'name': wizard_name,
            'view_mode': 'form',
            'views': [(False, "form")],
            'res_model': 'hr.expense.post.wizard',
            'res_id': self.env['hr.expense.post.wizard'].create({}).id,
            'target': 'new',
            'context': self.with_context(active_ids=self.ids).env.context,
        }

    def _post_without_wizard(self):
        """ Post an employee expense without any direct call for the wizard, should never be called unless in very specific flows """
        # When a move has been deleted
        self._check_can_create_move()
        today = fields.Date.context_today(self)
        employee_expenses = self.filtered(lambda expense: expense.payment_mode == 'own_account')

        for company, expenses in employee_expenses.grouped('company_id').items():
            expenses = expenses.with_company(company)
            company_domain = self.env['account.journal']._check_company_domain(company)
            journal = (
                    company.expense_journal_id
                    or expenses.env['account.journal'].search([*company_domain, ('type', '=', 'purchase')], limit=1))
            expense_receipt_vals_list = [
                {
                    **new_receipt_vals,
                    'journal_id': journal.id,
                    'invoice_date': today,
                }
                for new_receipt_vals in expenses._prepare_receipts_vals()
            ]
            moves = self.env['account.move'].sudo().create(expense_receipt_vals_list)
            for move in moves:
                move._message_set_main_attachment_id(move.attachment_ids, force=True, filter_xml=False)
            moves.action_post()

    def _create_company_paid_moves(self):
        """
        Creation of the account moves for the company paid expenses.
        -> Create an account payment (we only "log" the already paid expense so it can be reconciled)
        """
        self = self.with_context(clean_context(self.env.context))  # remove default_*
        company_account_expenses = self.filtered(lambda expense: expense.payment_mode == 'company_account')
        moves_sudo = self.env['account.move'].sudo()

        if company_account_expenses:
            move_vals_list, payment_vals_list = zip(*[expense._prepare_payments_vals() for expense in company_account_expenses])

            payment_moves_sudo = self.env['account.move'].sudo().create(move_vals_list)
            for payment_vals, move in zip(payment_vals_list, payment_moves_sudo):
                payment_vals['move_id'] = move.id

            payments_sudo = self.env['account.payment'].sudo().create(payment_vals_list)
            for payment_sudo, move_sudo in zip(payments_sudo, payment_moves_sudo):
                move_sudo.update({
                    'origin_payment_id': payment_sudo.id,
                    # We need to put the journal_id because editing origin_payment_id triggers a re-computation chain
                    # that voids the company_currency_id of the lines
                    'journal_id': move_sudo.journal_id.id,
                })

            moves_sudo |= payment_moves_sudo

        # returning the move with the superuser flag set back as it was at the origin of the call
        return moves_sudo.sudo(self.env.su)

    def _prepare_receipts_vals(self):
        attachments_data = []
        for attachment in self.message_main_attachment_id:
            attachments_data.append(
                Command.create(attachment.copy_data({'res_model': 'account.move', 'res_id': False, 'raw': attachment.raw})[0])
            )

        return_vals = []
        for employee_sudo, expenses_sudo in self.sudo().grouped('employee_id').items():
            multiple_expenses_name = _("Expenses of %(employee)s", employee=employee_sudo.name)
            move_ref = expenses_sudo.name if len(expenses_sudo) == 1 else multiple_expenses_name
            return_vals.append({
            **expenses_sudo._prepare_move_vals(),
                'ref': move_ref,
                'move_type': 'in_receipt',
                'partner_id': employee_sudo.work_contact_id.id,
                'commercial_partner_id': employee_sudo.user_partner_id.id,
                'currency_id': expenses_sudo.company_currency_id.id,
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
            raise UserError(_("You need to add a manual payment method on the journal (%s)", journal.name))

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
            'line_ids': [Command.create(line) for line in move_lines],
            'attachment_ids': [
                Command.create(attachment.copy_data({'res_model': 'account.move', 'res_id': False, 'raw': attachment.raw})[0])
                for attachment in self.message_main_attachment_id]
        }
        return move_vals, payment_vals

    def _prepare_move_vals(self):
        return {
            # force the name to the default value, to avoid an eventual 'default_name' in the context
            # that would set it to '' which would then cause no number to be given to the account.move
            # when it is posted.
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
        return _('%(employee_name)s: %(expense_name)s', employee_name=self.employee_id.name, expense_name=expense_name)

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
            account = self.product_id.product_tmpl_id._get_product_accounts()['expense']
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
        self.ensure_one()
        if self.payment_mode == 'company_account':
            account_dest = self.payment_method_line_id.payment_account_id or self._get_outstanding_account_id()
        else:
            if not self.employee_id.sudo().work_contact_id:
                raise UserError(
                    _("No work contact found for the employee %(name)s, please configure one.", name=self.employee_id.name)
                )
            partner = self.employee_id.sudo().work_contact_id.with_company(self.company_id)
            account_dest = partner.property_account_payable_id or partner.parent_id.property_account_payable_id
        return account_dest.id

    def _get_outstanding_account_id(self):
        account_ref = 'account_journal_payment_debit_account_id' if self.payment_method_line_id.payment_type == 'inbound' else 'account_journal_payment_credit_account_id'
        chart_template = self.with_context(allowed_company_ids=self.company_id.root_id.ids).env['account.chart.template']
        outstanding_account = chart_template.ref(account_ref, raise_if_not_found=False)
        if not self.company_id.chart_template:
            action = self.env.ref('account.action_account_config')
            raise RedirectWarning(_('You should install a Fiscal Localization first.'), action.id, _('Accounting Settings'))
        if not outstanding_account:
            bank_prefix = self.company_id.bank_account_code_prefix
            template_data = chart_template._get_chart_template_data(self.company_id.chart_template).get('template_data')
            code_digits = int(template_data.get('code_digits', 6))
            chart_template._create_outstanding_accounts(self.company_id, bank_prefix, code_digits)
            outstanding_account = chart_template.ref(account_ref, raise_if_not_found=False)
        if not outstanding_account.active:
            raise RedirectWarning(
                message=_("The account %(name)s (%(code)s) is archived. Activate it to continue", name=outstanding_account.name, code=outstanding_account.code),
                action=outstanding_account._get_records_action(),
                button_text=_("Go to Account"),
            )
        return outstanding_account

    def _creation_message(self):
        if self.env.context.get('from_split_wizard'):
            return _("Expense created from a split.")
        return super()._creation_message()
