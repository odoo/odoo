# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import contextlib
import logging
import re
from datetime import timedelta

import psycopg2
import werkzeug
from markupsafe import Markup

from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, RedirectWarning, UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import SQL, clean_context, email_normalize, float_repr, float_round, format_amount, format_date, is_html_empty

_logger = logging.getLogger(__name__)

EXPENSE_APPROVAL_STATE = [
    ('submitted', "Submitted"),
    ('approved', "Approved"),
    ('refused', "Refused"),
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
    _mail_post_access = 'read'

    @api.model
    def _default_employee_id(self):
        employee = self.env.user.employee_id
        if not employee and not self.env.user.has_group('hr_expense.group_hr_expense_team_approver'):
            raise ValidationError(self.env._('The current user has no related employee. Please, create one.'))
        return employee

    name = fields.Char(
        string="Description",
        compute='_compute_name', precompute=True, store=True, readonly=False,
        copy=True,
    )
    date = fields.Date(string="Date", default=fields.Date.context_today)
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string="Employee",
        compute='_compute_employee_id', precompute=True, store=True, readonly=False,
        index=True,
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
        index=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    # product_id is not required to allow to create an expense without product via mail alias, but should be required on the view.
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        tracking=True,
        check_company=True,
        domain=[('can_be_expensed', '=', True)],
        index=True,
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
            # Payment states
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
    marked_as_paid = fields.Boolean(string="Marked as Paid", copy=False)
    approval_date = fields.Datetime(string="Approval Date", readonly=True)
    duplicate_expense_ids = fields.Many2many(comodel_name='hr.expense', compute='_compute_duplicate_expense_ids')  # Used to trigger warnings
    same_receipt_expense_ids = fields.Many2many(comodel_name='hr.expense', compute='_compute_same_receipt_expense_ids')  # Used to trigger warnings
    last_notification_date = fields.Datetime(string="Last Notification Date", readonly=True, copy=False)

    split_expense_origin_id = fields.Many2one(
        comodel_name='hr.expense',
        string="Origin Split Expense",
        help="Original expense from a split.",
    )
    split_expense_count = fields.Integer(string="Number of Split Expenses", compute='_compute_split_expense_count')
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
    price_unit = fields.Float(
        string="Unit Price",
        compute='_compute_price_unit', precompute=True, store=True, required=True, readonly=True,
        copy=True,
        min_display_digits='Product Price',
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

    payment_mode = fields.Selection(
        selection=[
            ('own_account', "Employee (Through a Purchase Receipt)"),
            ('company_account', "None (Paid by Company)")
        ],
        string="Reimbursement",
        default='own_account',
        required=True,
        tracking=True,
    )
    vendor_id = fields.Many2one(comodel_name='res.partner', string="Vendor")

    # Security fields
    is_editable = fields.Boolean(string="Is Editable By Current User", compute='_compute_is_editable', readonly=True)
    is_own_expense = fields.Boolean(compute='_compute_is_own_expense')
    can_reset = fields.Boolean(string='Can Reset', compute='_compute_can_reset', readonly=True)
    can_approve = fields.Boolean(string='Can Approve', compute='_compute_can_approve', readonly=True)

    # Legacy sheet field, allow grouping of expenses to keep the grouping mechanic data and allow it to be re-used when re-implemented
    former_sheet_id = fields.Integer(string='Former Report')

    # --------------------------------------------
    # Constraints
    # --------------------------------------------

    _check_date_not_draft = models.Constraint(
        "CHECK(state = 'draft' OR date IS NOT NULL)",
        "You cannot submit or process an expense without a date. Please set a date first.",
    )

    @api.constrains('state', 'name', 'product_id', 'total_amount', 'total_amount_currency')
    def _check_required_fields(self):
        for expense in self.filtered(lambda expense: expense.state != 'draft'):
            errors = []

            # Check for required fields 'name' and 'product_id'
            if not expense.name and not expense.product_id and expense.state != 'refused':
                errors.append(self.env._("Enter a description and select a product to proceed."))
            elif not expense.name:
                errors.append(self.env._("Enter a description to proceed."))
            elif not expense.product_id and expense.state != 'refused':
                errors.append(self.env._("Select a product to proceed."))
            # Check for required field 'employee_id'
            if not expense.employee_id:
                errors.append(self.env._("Select an employee to proceed."))

            # Check for non-zero amounts
            total_amount_is_zero = expense.company_currency_id.is_zero(expense.total_amount)
            total_amount_currency_is_zero = expense.currency_id.is_zero(expense.total_amount_currency)
            if total_amount_is_zero or total_amount_currency_is_zero:
                errors.append(self.env._("Only draft expenses can have a total of 0."))

            if errors:
                raise ValidationError("\n".join(errors))

    # --------------------------------------------
    # Compute methods
    # --------------------------------------------

    @api.depends('product_has_cost')
    def _compute_currency_id(self):
        for expense in self:
            if expense.product_has_cost and expense.state == 'draft':
                expense.currency_id = expense.company_currency_id

    @api.depends_context('uid')
    @api.depends('employee_id.user_id')
    def _compute_is_own_expense(self):
        for expense in self:
            expense.is_own_expense = expense.employee_id.user_id == self.env.user

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
            if (
                not expense.company_id
                or (expense.state not in {'draft', 'submitted', 'approved'} and not self.env.su)
            ):
                # When emptying the required company_id field, onchanges are triggered.
                # To avoid recomputing the interface without a company (which could
                # temporarily make fields editable), we do not recompute anything and wait
                # for a proper company to be set. The interface is also made not editable
                # when the state is not draft/submitted/approved and the user is not a superuser.
                expense.is_editable = False
                continue

            if is_hr_admin:
                # Administrator-level users are not restricted, they can edit their own expenses
                expense.is_editable = True
                continue

            employee = expense.employee_id
            if expense.is_own_expense and expense.state == 'draft':
                # Anyone can edit their own draft expense
                expense.is_editable = True
                continue

            managers = (
                expense.manager_id
                | employee._get_expense_managers()
            )
            if is_all_approver:
                managers |= self.env.user
            if expense.employee_id.id in expenses_employee_ids_under_user_ones:
                managers |= self.env.user
            if not expense.is_own_expense and self.env.user in managers:
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
            expense.label_currency_rate = self.env._(
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

    @api.onchange('name')
    def _onchange_predict_product(self):
        if self.name and not self.product_id:
            predicted_product_id = self._predict_product(self.name)
            default_product = self.env['product.product'].search([('can_be_expensed', '=', True)])
            if default_product:
                default_product = default_product.filtered(lambda p: p.default_code == "EXP_GEN")[:1] or default_product[0]
                self.product_id = predicted_product_id if predicted_product_id else default_product

    @api.depends('product_id')
    def _compute_from_product(self):
        for expense in self:
            expense.product_has_cost = expense.product_id and not expense.company_currency_id.is_zero(expense.product_id.standard_price)

    @api.depends('product_id.uom_id')
    def _compute_uom_id(self):
        for expense in self:
            expense.product_uom_id = expense.product_id.uom_id

    @api.depends('approval_state', 'marked_as_paid')
    def _compute_state(self):
        """
        Compute the states of the expense as such (priority is given to the last matching state of the list):
            - draft: By default
            - submitted: When the approval_state is 'submitted'
            - approved: When the approval_state is 'approved' or the linked move state is 'draft'
            - refused: When the approval_state is 'refused'
            - paid: When it is a company paid expense or the move state is neither 'draft' nor 'posted'
        """
        for expense in self:
            paid_status = expense._get_paid_status()
            if paid_status:
                expense.state = paid_status
            else:
                expense.state = expense.approval_state or 'draft'

    @api.depends('employee_id', 'employee_id.department_id')
    def _compute_from_employee_id(self):
        for expense in self:
            expense.department_id = expense.employee_id.department_id
            expense.manager_id = expense._get_default_responsible_for_approval()

    @api.depends('quantity', 'price_unit')
    def _compute_total_amount_currency(self):
        for expense in self.filtered('product_has_cost'):
            expense.total_amount_currency = expense.quantity * expense.price_unit

    @api.onchange('total_amount_currency')
    def _inverse_total_amount_currency(self):
        for expense in self:
            if not expense.is_editable:
                raise UserError(self.env._(
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
        for expense in self:
            if not expense.company_id:
                # This would be happening when emptying the required company_id field, triggering the "onchange"s.
                # A traceback would occur because company_currency_id would be set to False.
                # Instead of using the env company, recomputing the interface just to be blocked when trying to save
                # we choose not to recompute anything and wait for a proper company to be inputted.
                continue

            if expense.is_multiple_currency:
                expense.total_amount = expense.total_amount_currency * expense.currency_rate
            else:
                expense.total_amount = expense.total_amount_currency

    def _inverse_total_amount(self):
        """ Allows to set a custom rate on the expense, and avoid the override when it makes no sense """
        for expense in self:
            if not expense.is_multiple_currency:
                expense.total_amount_currency = expense.total_amount
            expense.currency_rate = expense.total_amount / expense.total_amount_currency if expense.total_amount_currency else 1.0
            expense.price_unit = expense.total_amount / expense.quantity if expense.quantity else expense.total_amount

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
            ('res_id', '!=', False),
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

    @api.depends('product_id', 'employee_id')
    def _compute_analytic_distribution(self):
        for expense in self:
            distribution = self.env['account.analytic.distribution.model']._get_distribution({
                'product_id': expense.product_id.id,
                'product_categ_id': expense.product_id.categ_id.id,
                'partner_id': expense.employee_id.work_contact_id.id,
                'partner_category_id': expense.employee_id.work_contact_id.category_id.ids,
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
    def write(self, vals):

        changed_fields_set = set(vals)
        if {'is_editable', 'can_approve', 'can_refuse'} & changed_fields_set:
            raise UserError(self.env._("You cannot edit the security fields of an expense manually"))

        readonly_expenses = self.filtered(lambda e: not e.is_editable)
        if not self.env.su and readonly_expenses:
            is_unauthorised_edit = (
                {'tax_ids', 'manager_id'} & changed_fields_set
                or (
                    {'analytic_distribution', 'account_id'} & changed_fields_set
                )
            )
            if is_unauthorised_edit:
                raise UserError(self.env._(
                    "Uh-oh! You can’t edit this expense.\n\n"
                    "Reach out to the administrators, flash your best smile, and see if they'll grant you the magical access you seek.",
                ))

        res = super().write(vals)

        if vals.get('state') == 'approved' or vals.get('approval_state') == 'approved':
            # filter out auto approved expenses
            self.filtered(lambda expense:
                expense.manager_id - expense.employee_id.user_id
                or expense.employee_id.expense_manager_id
            )._check_can_approve()
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
        use_mailgateway = self.env['ir.config_parameter'].sudo().get_bool('hr_expense.use_mailgateway')
        expense_alias = self.env.ref('hr_expense.mail_alias_expense', raise_if_not_found=False) if use_mailgateway else False
        if expense_alias and expense_alias.alias_domain and expense_alias.alias_name:
            # encode, but force %20 encoding for space instead of a + (URL / mailto difference)
            params = werkzeug.urls.url_encode({'subject': self.env._("Lunch with customer $12.32")}).replace('+', '%20')
            return Markup(
                """<div class="text-muted mt-4">%(send_string)s <a class="text-body" href="mailto:%(alias_email)s?%(params)s">%(alias_email)s</a></div>"""
            ) % {
                'alias_email': expense_alias.display_name,
                'params': params,
                'send_string': self.env._("Tip: try sending receipts by email"),
            }
        return ""

    def _track_log_get_default_body(self, track_init_values):
        if (
            'state' in track_init_values
            and track_init_values.get('state') != 'paid'
            and self.state == 'paid'
            and self.payment_mode != 'company_account'
        ):
            reimbursed_amount = self.total_amount
            return Markup(
                '<div>%(label)s: <strong>%(amount)s</strong></div>'
            ) % {
                'label': self.env._('Amount reimbursed'),
                'amount': format_amount(self.env, reimbursed_amount, self.company_currency_id),
            }

        return super()._track_log_get_default_body(track_init_values)

    def _track_log_get_default_subtype(self, track_init_values):
        self.ensure_one()
        if 'state' not in track_init_values:
            return super()._track_log_get_default_subtype(track_init_values)

        match self.state:
            case 'draft':
                return self.env.ref('hr_expense.mt_expense_reset')
            case 'refused':
                return self.env.ref('hr_expense.mt_expense_refused')
            case 'paid':
                return self.env.ref('hr_expense.mt_expense_paid')
            case 'approved':
                if track_init_values['state'] == 'paid':  # Reverting state
                    subtype = 'hr_expense.mt_expense_entry_delete'
                    return self.env.ref(subtype)
                return self.env.ref('hr_expense.mt_expense_approved')
            case _:
                return super()._track_log_get_default_subtype(track_init_values)

    def update_activities_and_mails(self):
        """ Update the "Review this expense" activity with the new state of the expense, also sends mail to approver to ask them to act """
        expenses_activity_done = self.env['hr.expense']
        expenses_activity_unlink = self.env['hr.expense']
        expenses_submitted_to_review = self.env['hr.expense']
        for expense in self:
            if expense.state == 'submitted':
                expense.with_context(mail_activity_quick_update=True).activity_schedule(
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

        if expenses_submitted_to_review:
            expenses_submitted_to_review._send_submitted_expenses_mail()

    def _send_submitted_expenses_mail(self):
        """
        Send submitted email to manager if no email was sent recently
        """
        new_mails = []
        other_expenses_map = {
            (company.id, manager.id): {
                'expenses': expenses,
                'last_notification_date': max_date
            }
            for company, manager, expenses, max_date in self.sudo()._read_group(
                domain=[
                    ('id', 'not in', self.ids),
                    ('state', '=', 'submitted'),
                    ('manager_id', 'in', self.mapped('manager_id').ids),
                    ('company_id', 'in', self.mapped('company_id').ids),
                ],
                groupby=['company_id', 'manager_id'],
                aggregates=['id:recordset', 'last_notification_date:max'],
            )
        }
        recent_threshold = fields.Datetime.now() - timedelta(hours=12)
        for company, expenses_submitted_per_company in self.grouped('company_id').items():
            parent_company_mails = company.parent_ids[::-1].mapped('email_formatted')
            mail_from = (
                    self.env.user.email
                    or company.email_formatted
                    or (parent_company_mails and parent_company_mails[0])
            )

            if not mail_from:  # We can't send a mail without sender
                _logger.warning(self.env._("Failed to send mails for submitted expenses. No valid email was found for the company"))
                continue

            for manager, expenses_submitted in expenses_submitted_per_company.grouped('manager_id').items():
                if not manager:
                    continue
                other_expenses_with_date = other_expenses_map.get((company.id, manager.id), {})
                last_notification_date = other_expenses_with_date.get('last_notification_date')

                if last_notification_date and last_notification_date > recent_threshold:
                    continue

                all_submitted_expenses = other_expenses_with_date.get('expenses', self.env['hr.expense'])
                all_submitted_expenses |= expenses_submitted

                manager_langs = tuple(lang for lang in manager.partner_id.mapped('lang') if lang)
                mail_lang = (manager_langs and manager_langs[0]) or self.env.lang or 'en_US'
                employee_breakdown = []
                for employee, expenses in all_submitted_expenses.grouped('employee_id').items():
                    employee_breakdown.append({
                        'name': employee.name,
                        'amount': format_amount(self.env, sum(expenses.mapped('total_amount')), company.currency_id),
                    })

                body = self.env['ir.qweb']._render(
                    template='hr_expense.hr_expense_template_submitted_expenses',
                    values={
                        'manager_name': manager.name,
                        'url': f'/odoo/{manager.id}/expenses-to-process',
                        'company': company,
                        'user': self.env.user,
                        'total_amount': sum(expenses_submitted.mapped('total_amount')),
                        'today_string': format_date(self.env, fields.Date.context_today(self), date_format='EEEE', lang_code=mail_lang),
                        'first_expense_name': expenses_submitted[0].name,
                        'expenses_count': len(all_submitted_expenses),
                        'employee_breakdown': employee_breakdown,
                    },
                    lang=mail_lang,
                )
                new_mails.append({
                    'author_id': self.env.user.partner_id.id,
                    'auto_delete': True,
                    'body_html': body,
                    'email_from': mail_from,
                    'email_to': manager.employee_id.work_email or manager.email,
                    'subject': self.env._("New expenses waiting for your approval"),
                })
                all_submitted_expenses.last_notification_date = fields.Datetime.now()
        if new_mails:
            self.env['mail.mail'].sudo().create(new_mails).send()

    @api.model
    def get_empty_list_help(self, help_message):
        return super().get_empty_list_help((help_message or '') + self._get_empty_list_mail_alias())

    @api.model
    def get_views(self, views, options=None):
        res = super().get_views(views, options)
        form_toolbar = res['views'].get('form', {}).get('toolbar', {})
        report = self.env.ref('hr_expense.action_report_hr_expense', raise_if_not_found=False)
        if form_toolbar.get('print') and report:
            form_toolbar['print'] = [
                dict(action, name=self.env._("Print"))
                if action['id'] == report.id else action
                for action in form_toolbar['print']
            ]
        return res

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        email_address = email_normalize(msg_dict.get('email_from'))
        employee = self._get_employee_from_email(email_address)

        if not employee:
            return super().message_new(msg_dict, custom_values=custom_values)

        expense_description = msg_dict.get('subject', '')

        company = employee.company_id
        currencies = company.currency_id

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
            'quantity': 1,
            'company_id': company.id,
            'currency_id': currency_id.id
        }

        expense = super().message_new(msg_dict, dict(custom_values or {}, **vals))
        self._send_expense_success_mail(msg_dict, expense)
        return expense

    # ----------------------------------------
    # Actions
    # ----------------------------------------

    def action_open_split_expense(self):
        self.ensure_one()
        split_expense_ids = self.search([('split_expense_origin_id', '=', self.split_expense_origin_id.id)])
        return split_expense_ids._get_records_action(name=self.env._("Split Expenses"))

    def action_submit(self):
        """ Submit a draft expense to an approve, may skip to the approval step if no approver on the employee nor the expense """
        user = self.env.user
        for expense in self:
            if user.employee_id != expense.employee_id and not expense.can_approve:
                raise UserError(self.env._("You do not have the required permission to submit this expense."))
            if not expense.manager_id:
                expense.sudo().manager_id = expense._get_default_responsible_for_approval()
        expenses_autovalidated = self.filtered(lambda expense: expense._can_be_autovalidated())
        (self - expenses_autovalidated).approval_state = 'submitted'
        if expenses_autovalidated:  # Note, this will and should bypass the duplicate check. May be changed later
            expenses_autovalidated._do_approve()
        self.sudo().update_activities_and_mails()

    def _can_be_autovalidated(self):
        """ Check whether the given expenses can be auto-validated (no approver) """
        self.ensure_one()
        return (
            (not self.manager_id and not self.employee_id.expense_manager_id)
            or self.manager_id == self.employee_id.user_id
        )

    def action_approve(self):
        """ Approve an expense, pops a wizard if a duplicated expense is found to confirm they are all valid expenses """
        self._check_can_approve()
        duplicates = self.duplicate_expense_ids.filtered(lambda exp: exp.state in {'submitted', 'approved', 'paid'})
        if duplicates:
            action = self.env["ir.actions.act_window"]._for_xml_id('hr_expense.hr_expense_approve_duplicate_action')
            action['context'] = {'default_expense_ids': duplicates.ids}
            return action
        self._do_approve()

    def action_refuse(self):
        """ Refuse an expense with a reason """
        self._check_can_refuse()
        refuse_wizard = self.env["ir.actions.act_window"]._for_xml_id('hr_expense.hr_expense_refuse_wizard_action')
        refuse_wizard['context'] = dict(ast.literal_eval(refuse_wizard['context']), default_expense_ids=self.ids)
        return refuse_wizard

    def action_pay(self):
        """ Mark an expense as paid """
        self._check_can_pay()
        unpaid_expenses = self.filtered(lambda expense: not expense.marked_as_paid)
        unpaid_expenses.marked_as_paid = True
        return {}  # In overrides we can return an action to open a payment wizard

    def action_reset(self):
        """  Reset an expense to draft state, reversing the accounting entries if needed """
        self._check_can_reset_approval()
        self._do_reset_approval()

    def attach_document(self, **kwargs):
        """When an attachment is uploaded as a receipt, set it as the main attachment."""
        if not self.has_access('write') and self.employee_id.user_id != self.env.user:
            raise AccessError(self.env._("You don't have the access rights to modify this expense."))
        attachment_ids = [attachment_id for attachment_id in kwargs.get('attachment_ids', []) if attachment_id]  # Filter out falsy values
        if not attachment_ids:
            # If uploading the document fails due to the checks in the create method of ir.attachment, the
            # attachment_ids will contains [None], so we need to check here to raise the UserError.
            raise UserError(self.env._("You can't add an attachment to an expense once it has been approved."))

        attachment = self.env['ir.attachment'].browse(attachment_ids[-1:])
        user_expenses = self.filtered(lambda expense: expense.employee_id.user_id == self.env.user)
        user_expenses.sudo()._message_set_main_attachment_id(attachment, force=True)
        (self - user_expenses)._message_set_main_attachment_id(attachment, force=True)

    @api.model
    def create_expense_from_attachments(self, attachment_ids=None, view_type='list'):
        """
            Create the expenses from files.

            :return: An action redirecting to hr.expense list view.
        """
        if not attachment_ids:
            raise UserError(self.env._("No attachment was provided"))
        attachments = self.env['ir.attachment'].browse(attachment_ids)
        expenses = self.env['hr.expense']

        if any(attachment.res_id or attachment.res_model != 'hr.expense' for attachment in attachments):
            raise UserError(self.env._("Invalid attachments!"))

        for attachment in attachments:
            expense = self.env['hr.expense'].create([{
                'price_unit': 0,
            }])
            attachment.write({'res_model': 'hr.expense', 'res_id': expense.id})

            expense._message_set_main_attachment_id(attachment, force=True)
            expenses += expense
        return expenses.ids

    def action_show_same_receipt_expense_ids(self):
        self.ensure_one()
        return self.same_receipt_expense_ids._get_records_action(
            name=self.env._("Expenses with a similar receipt to %(other_expense_name)s", other_expense_name=self.name),
        )

    def action_show_duplicate_expense_ids(self):
        self.ensure_one()
        duplicate_expenses = self.duplicate_expense_ids - self
        return duplicate_expenses._get_records_action(
            name=self.env._("Expenses similar to %(other_expense_name)s", other_expense_name=self.name),
        )

    @api.model
    def get_expense_dashboard(self, domain=None):
        expense_state = {
            'draft': {
                'description': self.env._("To Submit"),
                'amount': 0.0,
                'currency': self.env.company.currency_id.id,
            },
            'submitted': {
                'description': self.env._("Waiting Approval"),
                'amount': 0.0,
                'currency': self.env.company.currency_id.id,
            },
            'approved': {
                'description': self.env._("Waiting Reimbursement"),
                'amount': 0.0,
                'currency': self.env.company.currency_id.id,
            }
        }
        if not self.env.user.employee_ids:
            return expense_state
        # Counting the expenses to display in the dashboard:
        # - To Submit: contains the expenses paid either by the employee or by the company, and that are draft or reported
        # - Waiting approval: contains expenses paid by the employee or paid by the company, and that have been submitted but still need to be approved/refused
        # - To be reimbursed: contains ONLY expenses paid by the employee that are approved or posted, the payment has not yet been made
        base_domain = [
            ('employee_id', 'child_of', self.env.user.employee_ids.ids),
            '|', ('state', 'in', ('draft', 'submitted')),
            '&', ('payment_mode', '=', 'own_account'), ('state', '=', 'approved')
        ]
        if domain:
            base_domain = Domain.AND([base_domain, domain])

        fetched_expenses = self._read_group(base_domain, ['state'], ['total_amount:sum'])
        for state, total_amount_sum in fetched_expenses:
            expense_state['approved' if state == 'posted' else state]['amount'] += total_amount_sum
        return expense_state

    def action_approve_duplicates(self):
        root = self.env['ir.model.data']._xmlid_to_res_id("base.partner_root")
        for expense in self.duplicate_expense_ids:
            expense.message_post(
                body=self.env._('%(user)s confirms this expense is not a duplicate with similar expense.', user=self.env.user.name),
                author_id=root,
            )

    def action_split_wizard(self):
        """ Split the expense into several smaller ones """
        self.ensure_one()
        if self.state == 'paid':
            raise UserError(self.env._("You cannot split an expense that is already paid."))
        if not self.is_editable('is_editable'):
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

    # ----------------------------------------
    # Business
    # ----------------------------------------

    @api.model
    def _get_paid_states(self):
        return ('paid',)

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

    def _check_can_approve(self):
        if not all(self.mapped('can_approve')):
            reasons_list = tuple(reason for reason in self._get_cannot_approve_reason().values() if reason)
            reasons = self.env._("You cannot approve:\n %(reasons)s", reasons="\n".join(reasons_list))
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
                reason = self.env._(
                    "%(expense_name)s: Your are neither a Manager nor a HR Officer of this expense's company",
                    expense_name=expense.name,
                )

            elif not is_expense_team_approver:
                reason = self.env._("%(expense_name)s: You are neither a Manager nor a HR Officer", expense_name=expense.name)

            elif not is_hr_admin:
                current_managers = (
                    expense_employee._get_expense_managers()
                    | expense.manager_id
                )
                if expense_employee.id in expenses_employee_ids_under_user_ones:
                    current_managers |= self.env.user

                if expense_employee.user_id == self.env.user:
                    reason = self.env._("%(expense_name)s: It is your own expense", expense_name=expense.name)

                elif self.env.user not in current_managers and not is_approver:
                    reason = self.env._("%(expense_name)s: It is not from your department", expense_name=expense.name)
            reasons_per_record_id[expense.id] = reason
        return reasons_per_record_id

    def _check_can_refuse(self):
        if not all(self.mapped('can_approve')):
            reasons = self.env._("You cannot refuse:\n%(reasons)s", reasons="\n".join(filter(None, self._get_cannot_approve_reason().values())))
            raise UserError(reasons)

    def _check_can_reset_approval(self):
        if not all(self.mapped('can_reset')):
            raise UserError(self.env._("Only HR Officers, accountants, or the concerned employee can reset to draft."))
        if any(state not in {False, 'draft'} for state in self.account_move_id.mapped('state')):
            raise UserError(self.env._("You cannot reset to draft an expense linked to a journal entry."))

    def _do_approve(self):
        expenses_to_approve = self.filtered(lambda s: s.state in {'submitted', 'draft'})
        if any(expense.has_existing_bill and not expense.existing_bill_id for expense in expenses_to_approve):
            raise UserError(self.env._("The existing bill must be set."))

        for expense in expenses_to_approve:
            expense.write({
                'approval_state': 'approved',
                'manager_id': self.env.user.id,
                'approval_date': fields.Datetime().now(),
            })
        self.update_activities_and_mails()
        expenses_to_approve._create_move()

    def _do_reset_approval(self):
        self.sudo().write({'approval_state': False, 'approval_date': False, 'last_notification_date': False, 'marked_as_paid': False})
        self.update_activities_and_mails()

    def _do_refuse(self, reason):
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

    def _get_paid_status(self):
        """ Method to be overriden for more complex paid status computation """
        self.ensure_one()
        return self.marked_as_paid

    def _creation_message(self):
        if self.env.context.get('from_split_wizard'):
            return self.env._("Expense created from a split.")
        return super()._creation_message()

    def _get_predict_postgres_dictionary(self):
        lang = self.env.context.get('lang') and self.env.context.get('lang')[:2]
        return {'fr': 'french'}.get(lang, 'english')

    def _predict_product(self, description):
        if not description:
            return False
        parsed_description = re.sub(r"[*&()|!':<]+", " ", description)
        parsed_description = ' | '.join(parsed_description.split())
        limit_parameter = self.env["ir.config_parameter"].sudo().get_int("expense.predict.history.limit") or 10000
        sql_query = SQL("""
            SELECT
                max(f.rel) AS ranking,
                f.product_id,
                count(coalesce(f.product_id, 1)) AS count
            FROM (
                SELECT
                    p_search.product_id,
                    ts_rank(p_search.document, query_plain) AS rel
                FROM (
                    SELECT
                        expense.product_id,
                        (setweight(to_tsvector(%(lang)s, expense.name), 'B'))
                        AS document
                    FROM hr_expense expense
                    WHERE expense.state IN %(paid_states)s
                        AND expense.company_id = %(company_id)s
                    ORDER BY expense.date DESC, expense.id DESC
                    LIMIT %(limit_parameter)s
                ) p_search,
                to_tsquery(%(lang)s, %(description)s) query_plain
                WHERE (p_search.document @@ query_plain)
            ) AS f
            JOIN product_product p ON p.id = f.product_id AND p.active
            GROUP BY f.product_id
            ORDER BY ranking desc, count desc
            """,
            lang=self._get_predict_postgres_dictionary(),
            company_id=self.company_id.id or self.env.company.id,
            limit_parameter=int(limit_parameter),
            description=parsed_description,
            paid_states=self._get_paid_states(),
        )
        # In case there is an error while parsing the to_tsquery (wrong character for example)
        # We don't want to have a traceback, instead return False
        with contextlib.suppress(psycopg2.errors.SyntaxError):
            with self.env.cr.savepoint():
                self.env.cr.execute(sql_query)
                result = self.env.cr.fetchone()
            if result:
                return result[1]

        return False
