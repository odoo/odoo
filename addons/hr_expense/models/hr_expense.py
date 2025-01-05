# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from markupsafe import Markup
import werkzeug

from odoo import api, fields, Command, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import email_normalize, float_repr, float_round, is_html_empty


class HrExpense(models.Model):
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
        string="Unit of Measure",
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
            ('draft', 'To Report'),
            ('reported', 'To Submit'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('done', 'Done'),
            ('refused', 'Refused')
        ],
        string="Status",
        compute='_compute_state', store=True, readonly=True,
        index=True,
        copy=False,
        default='draft',
    )
    sheet_id = fields.Many2one(
        comodel_name='hr.expense.sheet',
        string="Expense Report",
        domain="[('employee_id', '=', employee_id), ('company_id', '=', company_id)]",
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )
    approved_by = fields.Many2one(comodel_name='res.users', string="Approved By", related='sheet_id.user_id', tracking=False)
    approved_on = fields.Datetime(string="Approved On", related='sheet_id.approval_date')
    duplicate_expense_ids = fields.Many2many(comodel_name='hr.expense', compute='_compute_duplicate_expense_ids')  # Used to trigger warnings
    same_receipt_expense_ids = fields.Many2many(comodel_name='hr.expense', compute='_compute_same_receipt_expense_ids')  # Used to trigger warnings

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
    untaxed_amount_currency = fields.Monetary(
        string="Total Untaxed Amount In Currency",
        currency_field='currency_id',
        compute='_compute_tax_amount_currency', precompute=True, store=True,
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
    accounting_date = fields.Date(  # The date used for the accounting entries or the one we'd like to use if not yet posted
        related='sheet_id.accounting_date',
        string="Accounting Date",
        store=True,
        groups='account.group_account_invoice,account.group_account_readonly',
    )

    # Security fields
    is_editable = fields.Boolean(string="Is Editable By Current User", compute='_compute_is_editable')

    @api.depends('product_has_cost')
    def _compute_currency_id(self):
        for expense in self:
            if expense.product_has_cost and expense.state in {'draft', 'reported'}:
                expense.currency_id = expense.company_currency_id

    @api.depends('sheet_id.is_editable')
    def _compute_is_editable(self):
        for expense in self:
            if expense.sheet_id:
                expense.is_editable = expense.sheet_id.is_editable
            else:
                expense.is_editable = True

    @api.onchange('product_has_cost')
    def _onchange_product_has_cost(self):
        """ Reset quantity to 1, in case of 0-cost product. To make sure switching non-0-cost to 0-cost doesn't keep the quantity."""
        if not self.product_has_cost and self.state in {'draft', 'reported'}:
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
            expense.currency_rate = expense.env['res.currency']._get_conversion_rate(
                from_currency=expense.currency_id,
                to_currency=expense.company_currency_id,
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

            expense.label_currency_rate = _(
                '1 %(exp_cur)s = %(rate)s %(comp_cur)s',
                exp_cur=expense.currency_id.name,
                rate=float_repr(expense.currency_rate, 6),
                comp_cur=expense.company_currency_id.name,
            )

    @api.depends('currency_id', 'company_currency_id')
    def _compute_is_multiple_currency(self):
        for expense in self:
            expense.is_multiple_currency = expense.currency_id != expense.company_currency_id

    @api.depends('product_id')
    def _compute_from_product(self):
        for expense in self:
            expense.product_has_cost = expense.product_id and not expense.company_currency_id.is_zero(expense.product_id.standard_price)
            expense.product_has_tax = bool(expense.product_id.supplier_taxes_id.filtered_domain(self.env['account.tax']._check_company_domain(expense.company_id)))

    @api.depends('product_id.uom_id')
    def _compute_uom_id(self):
        for expense in self:
            expense.product_uom_id = expense.product_id.uom_id

    @api.depends('sheet_id', 'sheet_id.account_move_ids', 'sheet_id.state')
    def _compute_state(self):
        for expense in self:
            if not expense.sheet_id:
                expense.state = 'draft'
            elif expense.sheet_id.state == 'draft':
                expense.state = 'reported'
            elif expense.sheet_id.state == 'cancel':
                expense.state = 'refused'
            elif expense.sheet_id.state in {'approve', 'post'}:
                expense.state = 'approved'
            elif not expense.sheet_id.account_move_ids:
                expense.state = 'submitted'
            else:
                expense.state = 'done'

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
                raise UserError(_('You are not authorized to edit this expense.'))
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
            else:
                expense.total_amount_currency = expense.total_amount
                expense.tax_amount = expense.tax_amount_currency
            expense.currency_rate = expense.total_amount / expense.total_amount_currency if expense.total_amount_currency else 1.0
            expense.price_unit = expense.total_amount / expense.quantity if expense.quantity else expense.total_amount

    @api.depends('product_id', 'company_id')
    def _compute_tax_ids(self):
        for _expense in self:
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
             Note: as total_amount can be set directly by the user when the currency_rate is overriden,
             the tax must be computed after the total_amount.
        """
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
            else:  # Mono-currency case computation shortcut
                expense.tax_amount = expense.tax_amount_currency

    @api.depends('total_amount', 'total_amount_currency')
    def _compute_price_unit(self):
        """
           The price_unit is the unit price of the product if no product is set and no attachment overrides it.
           Otherwise it is always computed from the total_amount and the quantity else it would break the vendor bill
           when edited after creation.
        """
        for expense in self:
            if expense.state not in {'draft', 'reported'}:
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

    def _needs_product_price_computation(self):
        # Hook to be overridden.
        self.ensure_one()
        return self.product_has_cost

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

        expenses_with_attachments = self.filtered(lambda expense: expense.attachment_ids)
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

    @api.constrains('payment_mode')
    def _check_payment_mode(self):
        self.sheet_id._check_payment_mode()

    def _prepare_base_line_for_taxes_computation(self, **kwargs):
        self.ensure_one()
        return self.env['account.tax']._prepare_base_line_for_taxes_computation(
            self,
            **{
                'partner_id': self.vendor_id,
                'special_mode': 'total_included',
                'rate': self.currency_rate,
                **kwargs,
            },
        )

    def attach_document(self, **kwargs):
        """When an attachment is uploaded as a receipt, set it as the main attachment."""
        self._message_set_main_attachment_id(self.env["ir.attachment"].browse(kwargs['attachment_ids'][-1:]), force=True)

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
            attachment_name = '.'.join(attachment.name.split('.')[:-1])
            vals = {
                'name': attachment_name,
                'price_unit': 0,
                'product_id': product.id,
            }
            if product.property_account_expense_id:
                vals['account_id'] = product.property_account_expense_id.id
            expense = self.env['hr.expense'].create(vals)
            attachment.write({'res_model': 'hr.expense', 'res_id': expense.id})

            expense._message_set_main_attachment_id(attachment, force=True)
            expenses += expense
        return {
            'name': _('Generate Expenses'),
            'res_model': 'hr.expense',
            'type': 'ir.actions.act_window',
            'views': [[False, view_type], [False, "form"]],
            'domain': [('id', 'in', expenses.ids)],
            'context': self.env.context,
        }

    # ----------------------------------------
    # ORM Overrides
    # ----------------------------------------

    @api.ondelete(at_uninstall=False)
    def _unlink_except_posted_or_approved(self):
        for expense in self:
            if expense.state in {'done', 'approved'}:
                raise UserError(_('You cannot delete a posted or approved expense.'))

    def write(self, vals):
        expense_to_previous_sheet = {}
        if 'sheet_id' in vals:
            # Check access rights on the sheet
            self.env['hr.expense.sheet'].browse(vals['sheet_id']).check_access('write')

            # Store the previous sheet of the expenses to unlink the attachments later if needed
            for expense in self:
                expense_to_previous_sheet[expense] = expense.sheet_id

            # If the sheet_id is modified, we need to check that the expenses are not set to 0,
            # unless it's to unlink the sheet
            enforced_non_zero_expenses = self.env['hr.expense']
            if vals.get('sheet_id'):  # If sheet is linked, we need to check all the newly linked expenses in self
                enforced_non_zero_expenses = self
        else:  # If sheet_id is not modified, we need to check all the expenses in self linked to a sheet
            enforced_non_zero_expenses = self.filtered('sheet_id')

        if 'tax_ids' in vals or 'analytic_distribution' in vals or 'account_id' in vals:
            if any(not expense.is_editable for expense in self):
                raise UserError(_('You are not authorized to edit this expense report.'))

        if enforced_non_zero_expenses:
            enforced_non_zero_expenses.check_amount_not_zero(vals)

        res = super().write(vals)

        if 'currency_id' in vals:
            self._set_expense_currency_rate(date_today=fields.Date.context_today(self))
            for expense in self:
                expense.total_amount = expense.total_amount_currency * expense.currency_rate

        if 'employee_id' in vals:
            # In case expense has sheet which has only one expense_line_ids,
            # then changing the expense.employee_id triggers changing the sheet.employee_id too.
            # Otherwise we unlink the expense line from sheet, (so that the user can create a new report).
            if self.sheet_id:
                employees = self.sheet_id.expense_line_ids.mapped('employee_id')
                if len(employees) == 1:
                    self.sheet_id.write({'employee_id': vals['employee_id']})
                elif len(employees) > 1:
                    self.sheet_id = False
        if 'sheet_id' in vals:
            # The sheet_id has been modified, either by an explicit write on sheet_id of the expense,
            # or by processing a command on the sheet's expense_line_ids.
            # We need to delete the attachments on the previous sheet coming from the expenses that were modified,
            # and copy the attachments of the expenses to the new sheet,
            # if it's a no-op (writing same sheet_id as the current sheet_id of the expense),
            # nothing should be done (no unlink then copy of the same attachments)
            attachments_to_unlink = self.env['ir.attachment']
            for expense in self:
                previous_sheet = expense_to_previous_sheet[expense]
                checksums = set((expense.attachment_ids - previous_sheet.expense_line_ids.attachment_ids).mapped('checksum'))
                attachments_to_unlink += previous_sheet.attachment_ids.filtered(lambda att: att.checksum in checksums)
                if vals['sheet_id'] and expense.sheet_id != previous_sheet:
                    for attachment in expense.attachment_ids.with_context(sync_attachment=False):
                        attachment.copy({
                            'res_model': 'hr.expense.sheet',
                            'res_id': vals['sheet_id'],
                        })
            attachments_to_unlink.with_context(sync_attachment=False).unlink()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        expenses = super().create(vals_list)
        if self.env.context.get('check_total_amount_not_zero'):
            for expense, vals in zip(expenses, vals_list):
                expense.check_amount_not_zero(vals)
        return expenses

    def unlink(self):
        attachments_to_unlink = self.env['ir.attachment']
        for sheet in self.sheet_id:
            checksums = set((sheet.expense_line_ids.attachment_ids & self.attachment_ids).mapped('checksum'))
            attachments_to_unlink += sheet.attachment_ids.filtered(lambda att: att.checksum in checksums)
        attachments_to_unlink.with_context(sync_attachment=False).unlink()
        return super().unlink()

    @api.model
    def get_empty_list_help(self, help_message):
        return super().get_empty_list_help((help_message or '') + self._get_empty_list_mail_alias())

    @api.model
    def _get_empty_list_mail_alias(self):
        use_mailgateway = self.env['ir.config_parameter'].sudo().get_param('hr_expense.use_mailgateway')
        expense_alias = self.env.ref('hr_expense.mail_alias_expense') if use_mailgateway else False
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

    def get_expense_attachments(self):
        return self.attachment_ids.mapped('image_src')

    def check_amount_not_zero(self, vals):
        error_msgs = []
        if 'total_amount' in vals:
            if any(expense.company_currency_id.is_zero(vals['total_amount']) for expense in self):
                error_msgs.append(_("You cannot set the expense total to 0 if it's linked to a report."))
        if 'total_amount_currency' in vals:
            if any(expense.currency_id.is_zero(vals['total_amount_currency']) for expense in self):
                error_msgs.append(_("You cannot set the expense total in currency to 0 if it's linked to a report."))
        if error_msgs:
            raise UserError("\n".join(error_msgs))

    # ----------------------------------------
    # Actions
    # ----------------------------------------

    def action_show_same_receipt_expense_ids(self):
        self.ensure_one()
        return self.same_receipt_expense_ids._get_records_action(
            name=_("Expenses with a similar receipt to %(other_expense_name)s", other_expense_name=self.name),
        )

    def action_view_sheet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [[False, "form"]],
            'res_model': 'hr.expense.sheet',
            'target': 'current',
            'res_id': self.sheet_id.id
        }

    def _get_default_expense_sheet_values(self):
        # If there is an expense with total_amount == 0, it means that expense has not been processed by OCR yet
        expenses_with_amount = self.filtered(lambda expense: not (
            expense.currency_id.is_zero(expense.total_amount_currency)
            or expense.company_currency_id.is_zero(expense.total_amount)
            or (expense.product_id and not float_round(expense.quantity, precision_rounding=expense.product_uom_id.rounding))
        ))

        if any(expense.state != 'draft' or expense.sheet_id for expense in expenses_with_amount):
            raise UserError(_("You cannot report twice the same line!"))
        if not expenses_with_amount:
            raise UserError(_("You cannot report the expenses without amount!"))
        if len(expenses_with_amount.mapped('employee_id')) != 1:
            raise UserError(_("You cannot report expenses for different employees in the same report."))
        if any(not expense.product_id for expense in expenses_with_amount):
            raise UserError(_("You can not create report without category."))
        if len(self.company_id) != 1:
            raise UserError(_("You cannot report expenses for different companies in the same report."))

        # Check if two reports should be created
        own_expenses = expenses_with_amount.filtered(lambda x: x.payment_mode == 'own_account')
        company_expenses = expenses_with_amount - own_expenses
        create_two_reports = own_expenses and company_expenses

        sheets = (own_expenses, company_expenses) if create_two_reports else (expenses_with_amount,)
        values = []

        # We use a fallback name only when several expense sheets are created,
        # else we use the form view required name to force the user to set a name
        for todo in sheets:
            paid_by = 'company' if todo[0].payment_mode == 'company_account' else 'employee'
            sheet_name = self.env['hr.expense.sheet']._get_default_sheet_name(todo)
            if not sheet_name and len(sheets) > 1:
                sheet_name = _("New Expense Report, paid by %(paid_by)s", paid_by=paid_by)
            values.append({
                'company_id': self.company_id.id,
                'employee_id': self[0].employee_id.id,
                'name': sheet_name,
                'expense_line_ids': [Command.set(todo.ids)],
                'state': 'draft',
            })
        return values

    def get_expenses_to_submit(self):
        # if there ere no records selected, then select all draft expenses for the user
        if self:
            expenses = self.filtered(lambda expense: expense.state == 'draft' and not expense.sheet_id and expense.is_editable)
        else:
            expenses = self.env['hr.expense'].search([
                ('state', '=', 'draft'),
                ('sheet_id', '=', False),
                ('employee_id', '=', self.env.user.employee_id.id),
            ]).filtered(lambda expense: expense.is_editable)

        if not expenses:
            raise UserError(_('You have no expense to report'))
        return expenses.action_submit_expenses()

    def _create_sheets_from_expense(self):
        if self.filtered(lambda expense: not expense.is_editable):
            raise UserError(_('You are not authorized to edit this expense.'))
        sheets = self.env['hr.expense.sheet'].create(self._get_default_expense_sheet_values())
        return sheets

    def action_submit_expenses(self):
        sheets = self._create_sheets_from_expense()
        return {
            'name': _('New Expense Reports'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.expense.sheet',
            'context': self.env.context,
            'views': [[False, "list"], [False, "form"]] if len(sheets) > 1 else [[False, "form"]],
            'domain': [('id', 'in', sheets.ids)],
            'res_id': sheets.id if len(sheets) == 1 else False,
        }

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
            'expense_id': self.id,
        } for price in (price_round_up, price_round_down)]

    def action_split_wizard(self):
        self.ensure_one()
        splits = self.env['hr.expense.split'].create(self._get_split_values())

        wizard = self.env['hr.expense.split.wizard'].create({
            'expense_split_line_ids': splits.ids,
            'expense_id': self.id,
        })
        return {
            'name': _('Expense split'),
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

    def _get_move_line_name(self):
        """ Helper to get the name of the account move lines related to an expense """
        self.ensure_one()
        expense_name = self.name.split("\n")[0][:64]
        return _('%(employee_name)s: %(expense_name)s', employee_name=self.employee_id.name, expense_name=expense_name)

    def _prepare_payments_vals(self):
        self.ensure_one()

        journal = self.sheet_id.journal_id
        payment_method_line = self.sheet_id.payment_method_line_id
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
            'account_id': self.sheet_id._get_expense_account_destination(),
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
            **self.sheet_id._prepare_move_vals(),
            'ref': self.name,
            'date': self.date,  # Overidden from self.sheet_id._prepare_move_vals() so we can use the expense date for the account move date
            'journal_id': journal.id,
            'partner_id': self.vendor_id.id,
            'currency_id': self.currency_id.id,
            'line_ids': [Command.create(line) for line in move_lines],
            'attachment_ids': [
                Command.create(attachment.copy_data({'res_model': 'account.move', 'res_id': False, 'raw': attachment.raw})[0])
                for attachment in self.message_main_attachment_id]
        }
        return move_vals, payment_vals

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
        journal = self.sheet_id.journal_id
        if journal.type == 'purchase':
            account = journal.default_account_id

        return account

    def _prepare_move_lines_vals(self):
        self.ensure_one()
        account = self._get_base_account()

        return {
            'name': self._get_move_line_name(),
            'account_id': account.id,
            'quantity': self.quantity or 1,
            'price_unit': self.price_unit,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom_id.id,
            'analytic_distribution': self.analytic_distribution,
            'expense_id': self.id,
            'partner_id': False if self.payment_mode == 'company_account' else self.employee_id.sudo().work_contact_id.id,
            'tax_ids': [Command.set(self.tax_ids.ids)],
        }

    @api.model
    def get_expense_dashboard(self):
        expense_state = {
            'to_submit': {
                'description': _('to submit'),
                'amount': 0.0,
                'currency': self.env.company.currency_id.id,
            },
            'submitted': {
                'description': _('under validation'),
                'amount': 0.0,
                'currency': self.env.company.currency_id.id,
            },
            'approved': {
                'description': _('to be reimbursed'),
                'amount': 0.0,
                'currency': self.env.company.currency_id.id,
            }
        }
        if not self.env.user.employee_ids:
            return expense_state
        target_currency = self.env.company.currency_id
        # Counting the expenses to display in the dashboard:
        # - To submit: contains the expenses paid either by the employee or by the company, and that are draft or reported
        # - Under validation: contains expenses paid by the employee or paid by the company, and that have been submitted but still need to be approved/refused
        # - To be reimbursed: contains ONLY expenses paid by the employee that are approved, the payment has not yet been made
        expenses = self._read_group(
            [
                ('employee_id', 'in', self.env.user.employee_ids.ids),
                '|', '&', ('payment_mode', 'in', ('own_account', 'company_account')), ('state', 'in', ('draft', 'reported', 'submitted')),
                     '&', ('payment_mode', '=', 'own_account'), ('state', '=', 'approved')
            ], ['state'], ['total_amount:sum'])
        for state, total_amount_sum in expenses:
            if state in {'draft', 'reported'}:  # Fuse the two states into only one "To Submit" state
                state = 'to_submit'
            expense_state[state]['amount'] += total_amount_sum
        return expense_state

    # ----------------------------------------
    # Mail Thread
    # ----------------------------------------

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

    @api.model
    def _get_employee_from_email(self, email_address):
        if not email_address:
            return self.env['hr.employee']
        employee = self.env['hr.employee'].search([
            ('user_id', '!=', False),
            '|',
            ('work_email', 'ilike', email_address),
            ('user_id.email', 'ilike', email_address),
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
