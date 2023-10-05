# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from markupsafe import Markup
import werkzeug

from odoo import api, fields, Command, models, _
from odoo.tools import float_round
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import clean_context, format_date
from odoo.tools import email_split, float_repr, float_compare, is_html_empty


class HrExpense(models.Model):
    _name = "hr.expense"
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

    name = fields.Char('Description', compute='_compute_name', readonly=False, store=True, precompute=True, required=True, copy=True)
    date = fields.Date(default=fields.Date.context_today, string="Expense Date")
    accounting_date = fields.Date(string="Accounting Date", related='sheet_id.accounting_date', store=True, groups='account.group_account_invoice,account.group_account_readonly')
    employee_id = fields.Many2one('hr.employee', compute='_compute_employee_id', string="Employee", precompute=True,
        store=True, required=True, readonly=False, tracking=True,
        default=_default_employee_id, domain=[('filter_for_expense', '=', True)], check_company=True)
    # product_id not required to allow create an expense without product via mail alias, but should be required on the view.
    product_id = fields.Many2one(
        'product.product',
        string='Category',
        tracking=True,
        check_company=True,
        domain=[('can_be_expensed', '=', True)],
        ondelete='restrict',
    )
    product_description = fields.Html(compute='_compute_product_description')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', compute='_compute_product_uom_id',
        store=True, precompute=True, copy=True, readonly=True,
        domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', readonly=True, string="UoM Category")
    unit_amount = fields.Float("Unit Price", compute='_compute_unit_amount', readonly=False, store=True, precompute=True, required=True, copy=True,
        digits='Product Price')
    unit_amount_display = fields.Float("Unit Price Display", compute='_compute_unit_amount_display')
    quantity = fields.Float(required=True, digits='Product Unit of Measure', default=1)
    tax_ids = fields.Many2many('account.tax', 'expense_tax', 'expense_id', 'tax_id',
        compute='_compute_tax_ids', store=True, readonly=False, precompute=True,
        check_company=True,
        domain="[('type_tax_use', '=', 'purchase')]", string='Included taxes',
        help="Both price-included and price-excluded taxes will behave as price-included taxes for expenses.")
    amount_tax = fields.Monetary(string='Tax amount in Currency', help="Tax amount in currency", precompute=True, compute='_compute_amount_tax', store=True, currency_field='currency_id')
    amount_tax_company = fields.Monetary('Tax amount', help="Tax amount in company currency", precompute=True, compute='_compute_total_amount_company', store=True, currency_field='company_currency_id')
    total_amount = fields.Monetary("Total In Currency", precompute=True, compute='_compute_amount', store=True, currency_field='currency_id', tracking=True, readonly=False, inverse='_inverse_total_amount')
    untaxed_amount = fields.Monetary("Total Untaxed Amount In Currency", precompute=True, compute='_compute_amount_tax', store=True, currency_field='currency_id')
    company_currency_id = fields.Many2one('res.currency', string="Report Company Currency", related='company_id.currency_id', readonly=True)
    total_amount_company = fields.Monetary('Total', tracking=True, precompute=True,
        compute='_compute_total_amount_company', inverse='_inverse_total_amount_company', store=True, currency_field='company_currency_id', readonly=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', precompute=True, string='Currency', required=True, store=True, readonly=False,
        compute='_compute_currency_id', default=lambda self: self.env.company.currency_id)
    currency_rate = fields.Float(compute='_compute_currency_rate', tracking=True)
    account_id = fields.Many2one(
        'account.account',
        compute='_compute_account_id', store=True, readonly=False, precompute=True,
        string='Account',
        check_company=True,
        domain="[('account_type', 'not in', ('asset_receivable','liability_payable','asset_cash','liability_credit_card'))]",
        help="An expense account is expected",
    )
    description = fields.Text('Internal Notes')
    payment_mode = fields.Selection([
        ("own_account", "Employee (to reimburse)"),
        ("company_account", "Company")
    ], default='own_account', tracking=True, string="Paid By")
    attachment_number = fields.Integer('Number of Attachments', compute='_compute_attachment_number')
    state = fields.Selection(
        selection=[
            ('draft', 'To Report'),
            ('reported', 'To Submit'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('done', 'Done'),
            ('refused', 'Refused')
        ],
        string='Status', default='draft', index=True, copy=False,
        compute='_compute_state', readonly=True, store=True,
    )
    sheet_id = fields.Many2one('hr.expense.sheet', string="Expense Report", domain="[('employee_id', '=', employee_id), ('company_id', '=', company_id)]", readonly=True, copy=False)
    sheet_is_editable = fields.Boolean(compute='_compute_sheet_is_editable')
    approved_by = fields.Many2one('res.users', string='Approved By', related='sheet_id.user_id', tracking=False)
    approved_on = fields.Datetime(string='Approved On', related='sheet_id.approval_date')
    reference = fields.Char("Bill Reference")

    is_editable = fields.Boolean("Is Editable By Current User", compute='_compute_is_editable')
    is_ref_editable = fields.Boolean("Reference Is Editable By Current User", compute='_compute_is_ref_editable')
    product_has_cost = fields.Boolean("Is product with non zero cost selected", compute='_compute_product_has_cost')
    product_has_tax = fields.Boolean("Whether tax is defined on a selected product", compute='_compute_product_has_cost')
    same_currency = fields.Boolean("Is currency_id different from the company_currency_id", compute='_compute_same_currency')
    duplicate_expense_ids = fields.Many2many('hr.expense', compute='_compute_duplicate_expense_ids')

    sample = fields.Boolean()
    label_convert_rate = fields.Char(compute='_compute_label_convert_rate')

    def attach_document(self, **kwargs):
        pass

    @api.depends('product_has_cost')
    def _compute_currency_id(self):
        for expense in self.filtered("product_has_cost"):
            expense.currency_id = expense.company_currency_id

    @api.onchange('product_has_cost')
    def _onchange_product_has_cost(self):
        # Reset quantity to 1, in case of 0-cost product
        if not self.product_has_cost:
            self.quantity = 1

    @api.depends('currency_id', 'total_amount', 'date')
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
            if not expense.same_currency:
                if (
                        expense.currency_id != expense._origin.currency_id
                        or expense.total_amount != expense._origin.total_amount
                        or expense.date != expense._origin.date
                ):
                    expense.currency_rate = self.env['res.currency']._get_conversion_rate(
                        from_currency=expense.currency_id,
                        to_currency=expense.company_currency_id,
                        company=expense.company_id,
                        date=expense.date or date_today,
                    )
                else:
                    expense.currency_rate = expense.total_amount_company / expense.total_amount if expense.total_amount else 1.0
            else:
                expense.currency_rate = 1.0

    @api.depends('currency_id', 'company_currency_id')
    def _compute_same_currency(self):
        for expense in self:
            expense.same_currency = bool(not expense.company_id or (expense.currency_id and expense.currency_id == expense.company_currency_id))

    @api.depends('product_id.standard_price')
    def _compute_product_has_cost(self):
        for expense in self:
            expense.product_has_cost = expense.product_id and (float_compare(expense.product_id.standard_price, 0.0, precision_digits=2) != 0)
            tax_ids = expense.product_id.supplier_taxes_id.filtered_domain(self.env['account.tax']._check_company_domain(expense.company_id))
            expense.product_has_tax = bool(tax_ids)

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

    @api.depends('quantity', 'unit_amount', 'tax_ids')
    def _compute_amount(self):
        for expense in self:
            if not expense.product_has_cost:
                continue
            base_lines = [expense._convert_to_tax_base_line_dict(price_unit=expense.unit_amount, quantity=expense.quantity)]
            taxes_totals = self.env['account.tax']._compute_taxes(base_lines)['totals'][expense.currency_id]
            expense.total_amount = taxes_totals['amount_untaxed'] + taxes_totals['amount_tax']

    @api.depends('total_amount')
    def _compute_amount_tax(self):
        """
         Note: as total_amount can be set directly by the user (for product without cost) or needs to be computed (for product with cost),
        `untaxed_amount` can't be computed in the same method as `total_amount`.
        """
        for expense in self:
            base_lines = [expense._convert_to_tax_base_line_dict(price_unit=expense.total_amount)]
            taxes_totals = self.env['account.tax']._compute_taxes(base_lines)['totals'][expense.currency_id]
            expense.amount_tax = taxes_totals['amount_tax']
            expense.untaxed_amount = taxes_totals['amount_untaxed']

    def _convert_to_tax_base_line_dict(self, base_line=None, currency=None, price_unit=None, quantity=None):
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            base_line,
            currency=currency or self.currency_id,
            product=self.product_id,
            taxes=self.tax_ids,
            price_unit=price_unit or self.total_amount_company,
            quantity=quantity or 1,
            account=self.account_id,
            analytic_distribution=self.analytic_distribution,
            extra_context={'force_price_include': True},
        )

    @api.depends(
        'date',
        'currency_id',
        'company_id',
        'company_currency_id',
        'total_amount',
        'tax_ids',
        'product_id',
        'employee_id.user_id.partner_id',
        'quantity',
    )
    def _compute_total_amount_company(self):
        for expense in self:
            base_lines = [expense._convert_to_tax_base_line_dict(
                price_unit=expense.total_amount * expense.currency_rate,
                currency=expense.company_currency_id,
            )]
            taxes_totals = self.env['account.tax']._compute_taxes(base_lines)['totals'][expense.company_currency_id]
            expense.total_amount_company = taxes_totals['amount_untaxed'] + taxes_totals['amount_tax']
            expense.amount_tax_company = taxes_totals['amount_tax']

    def _inverse_total_amount_company(self):
        # Allows to set a custom rate on the expense
        for expense in self:
            if expense.same_currency:
                expense.total_amount = expense.total_amount_company
            base_lines = [expense._convert_to_tax_base_line_dict(
                price_unit=expense.total_amount_company,
                currency=expense.company_currency_id,
            )]
            taxes_totals = self.env['account.tax']._compute_taxes(base_lines)['totals'][expense.company_currency_id]

            expense.amount_tax_company = taxes_totals['amount_tax']
            expense.currency_rate = expense.total_amount_company / expense.total_amount if expense.total_amount else 1.0
            expense.unit_amount = expense.total_amount_company / expense.quantity if expense.quantity else expense.total_amount_company

    @api.depends('currency_rate')
    def _compute_label_convert_rate(self):
        records_with_diff_currency = self.filtered(lambda x: not x.same_currency and x.currency_id)
        (self - records_with_diff_currency).label_convert_rate = False
        for expense in records_with_diff_currency:
            rate_txt = _('1 %(exp_cur)s = %(rate)s %(comp_cur)s', exp_cur=expense.currency_id.name, rate=float_repr(expense.currency_rate, 6), comp_cur=expense.company_currency_id.name)
            expense.label_convert_rate = rate_txt

    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment']._read_group([('res_model', '=', 'hr.expense'), ('res_id', 'in', self.ids)], ['res_id'], ['__count'])
        attachment = dict(attachment_data)
        for expense in self:
            expense.attachment_number = attachment.get(expense._origin.id, 0)

    @api.depends('employee_id')
    def _compute_is_editable(self):
        is_account_manager = self.env.user.has_group('account.group_account_user') or self.env.user.has_group('account.group_account_manager')
        for expense in self:
            if expense.state in {'draft', 'reported'} or expense.sheet_id.state in {'draft', 'submit'}:
                expense.is_editable = True
            elif expense.sheet_id.state == 'approve':
                expense.is_editable = is_account_manager
            else:
                expense.is_editable = False

    @api.depends('sheet_id.is_editable', 'sheet_id')
    def _compute_sheet_is_editable(self):
        for expense in self:
            expense.sheet_is_editable = not expense.sheet_id or expense.sheet_id.is_editable

    @api.depends('employee_id')
    def _compute_is_ref_editable(self):
        is_account_manager = self.env.user.has_group('account.group_account_user') or self.env.user.has_group('account.group_account_manager')
        for expense in self:
            if expense.state in {'draft', 'reported'} or expense.sheet_id.state in {'draft', 'submit'}:
                expense.is_ref_editable = True
            else:
                expense.is_ref_editable = is_account_manager

    @api.depends_context('lang')
    @api.depends('product_id')
    def _compute_product_description(self):
        for expense in self:
            expense.product_description = not is_html_empty(expense.product_id.description) and expense.product_id.description

    @api.depends('unit_amount')
    def _compute_unit_amount_display(self):
        # DEPRECATED
        for expense in self:
            expense.unit_amount_display = expense.unit_amount if expense.product_has_cost else expense.total_amount_company

    @api.depends('product_id')
    def _compute_name(self):
        for expense in self:
            expense.name = expense.name or expense.product_id.display_name

    @api.depends('product_id')
    def _compute_product_uom_id(self):
        for expense in self:
            expense.product_uom_id = expense.product_id.uom_id

    @api.depends('product_id', 'attachment_number', 'currency_rate')
    def _compute_unit_amount(self):
        for expense in self:
            if expense.product_id and expense.product_has_cost and not expense.attachment_number or (expense.attachment_number and not expense.unit_amount):
                expense.unit_amount = expense.product_id._price_compute('standard_price', currency=expense.currency_id)[expense.product_id.id]
            else:  # Even if we don't add a product, the unit_amount is still used for the move.line balance computation
                expense.unit_amount = expense.company_currency_id.round(expense.total_amount_company / (expense.quantity or 1))

    @api.depends('product_id', 'company_id')
    def _compute_tax_ids(self):
        for expense in self:
            expense = expense.with_company(expense.company_id)
            expense.tax_ids = expense.product_id.supplier_taxes_id.filtered_domain(self.env['account.tax']._check_company_domain(expense.company_id))


    @api.depends('product_id', 'company_id')
    def _compute_account_id(self):
        for expense in self:
            if not expense.product_id:
                expense.account_id = self.env['ir.property'].with_company(expense.company_id)._get('property_account_expense_categ_id', 'product.category')
                continue
            expense = expense.with_company(expense.company_id)
            account = expense.product_id.product_tmpl_id._get_product_accounts()['expense']
            if account:
                expense.account_id = account

    @api.depends('company_id')
    def _compute_employee_id(self):
        if not self.env.context.get('default_employee_id'):
            for expense in self:
                expense.employee_id = self.env.user.with_company(expense.company_id).employee_id

    @api.depends('employee_id', 'product_id', 'total_amount')
    def _compute_duplicate_expense_ids(self):
        self.duplicate_expense_ids = [(5, 0, 0)]

        expenses = self.filtered(lambda e: e.employee_id and e.product_id and e.total_amount)
        if expenses.ids:
            duplicates_query = """
              SELECT ARRAY_AGG(DISTINCT he.id)
                FROM hr_expense AS he
                JOIN hr_expense AS ex ON he.employee_id = ex.employee_id
                                     AND he.product_id = ex.product_id
                                     AND he.date = ex.date
                                     AND he.total_amount = ex.total_amount
                                     AND he.company_id = ex.company_id
                                     AND he.currency_id = ex.currency_id
               WHERE ex.id in %(expense_ids)s
               GROUP BY he.employee_id, he.product_id, he.date, he.total_amount, he.company_id, he.currency_id
              HAVING COUNT(he.id) > 1
            """
            self.env.cr.execute(duplicates_query, {
                'expense_ids': tuple(expenses.ids),
            })
            duplicates = [x[0] for x in self.env.cr.fetchall()]

            for ids in duplicates:
                exp = expenses.filtered(lambda e: e.id in ids)
                exp.duplicate_expense_ids = [(6, 0, ids)]
                expenses = expenses - exp

    @api.depends('product_id', 'account_id')
    def _compute_analytic_distribution(self):
        for expense in self:
            distribution = self.env['account.analytic.distribution.model']._get_distribution({
                'product_id': expense.product_id.id,
                'product_categ_id': expense.product_id.categ_id.id,
                'account_prefix': expense.account_id.code,
                'company_id': expense.company_id.id,
            })
            expense.analytic_distribution = distribution or expense.analytic_distribution

    @api.onchange('total_amount')
    def _inverse_total_amount(self):
        for expense in self:
            expense.unit_amount = expense.total_amount_company / expense.quantity

    @api.constrains('payment_mode')
    def _check_payment_mode(self):
        self.sheet_id._check_payment_mode()

    @api.constrains('product_id', 'product_uom_id')
    def _check_product_uom_category(self):
        for expense in self:
            if expense.product_id and expense.product_uom_id.category_id != expense.product_id.uom_id.category_id:
                raise UserError(_(
                    'Selected Unit of Measure for expense %(expense)s does not belong to the same category as the Unit of Measure of product %(product)s.',
                    expense=expense.name, product=expense.product_id.name,
                ))

    def create_expense_from_attachments(self, attachment_ids=None, view_type='list'):
        ''' Create the expenses from files.
         :return: An action redirecting to hr.expense tree view.
        '''
        if attachment_ids is None:
            attachment_ids = []
        attachments = self.env['ir.attachment'].browse(attachment_ids)
        if not attachments:
            raise UserError(_("No attachment was provided"))
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
                'unit_amount': 0,
                'product_id': self.env.company.expense_product_id.id or product.id,
            }
            if product.property_account_expense_id:
                vals['account_id'] = product.property_account_expense_id.id
            expense = self.env['hr.expense'].create(vals)
            attachment.write({
                'res_model': 'hr.expense',
                'res_id': expense.id,
            })

            attachment.register_as_main_attachment()
            expenses += expense
        return {
            'name': _('Generate Expenses'),
            'res_model': 'hr.expense',
            'type': 'ir.actions.act_window',
            'views': [[False, view_type], [False, "form"]],
            'context': {'search_default_my_expenses': 1, 'search_default_no_report': 1},
        }

    # ----------------------------------------
    # ORM Overrides
    # ----------------------------------------

    @api.ondelete(at_uninstall=False)
    def _unlink_except_posted_or_approved(self):
        for expense in self:
            if expense.state in ['done', 'approved']:
                raise UserError(_('You cannot delete a posted or approved expense.'))

    def write(self, vals):
        if 'sheet_id' in vals:
            self.env['hr.expense.sheet'].browse(vals['sheet_id']).check_access_rule('write')
        if 'tax_ids' in vals or 'analytic_distribution' in vals or 'account_id' in vals:
            if any(not expense.is_editable for expense in self):
                raise UserError(_('You are not authorized to edit this expense report.'))
        if 'reference' in vals:
            if any(not expense.is_ref_editable for expense in self):
                raise UserError(_('You are not authorized to edit the reference of this expense report.'))
        res = super().write(vals)
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
        return res

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
                """<p>%(send_string)s <a href="mailto:%(alias_email)s?%(params)s">%(alias_email)s</a></p>"""
            ) % {
                'alias_email': expense_alias.display_name,
                'params': params,
                'send_string': _("Or send your receipts at"),
            }
        return ""

    # ----------------------------------------
    # Actions
    # ----------------------------------------

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
        # If there is an expense with total_amount_company == 0, it means that expense has not been processed by OCR yet
        expenses_with_amount = self.filtered(lambda expense: not float_compare(expense.total_amount_company, 0.0, precision_rounding=expense.company_currency_id.rounding) == 0)

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

        sheets = [own_expenses, company_expenses] if create_two_reports else [expenses_with_amount]
        values = []
        for todo in sheets:
            if len(todo) == 1:
                expense_name = todo.name
            else:
                dates = todo.mapped('date')
                min_date = format_date(self.env, min(dates))
                max_date = format_date(self.env, max(dates))
                expense_name = min_date if max_date == min_date else f'{min_date} - {max_date}'

            vals = {
                'company_id': self.company_id.id,
                'employee_id': self[0].employee_id.id,
                'name': expense_name,
                'expense_line_ids': [Command.set(todo.ids)],
                'state': 'draft',
            }
            values.append(vals)
        return values

    def get_expenses_to_submit(self):
        # if there ere no records selected, then select all draft expenses for the user
        if self:
            expenses = self.filtered(lambda e: e.state == 'draft' and not e.sheet_id)
        else:
            expenses = self.env['hr.expense'].search([('state', '=', 'draft'), ('sheet_id', '=', False), ('employee_id', '=', self.env.user.employee_id.id)])

        if not expenses:
            raise UserError(_('You have no expense to report'))
        return expenses.action_submit_expenses()

    def action_submit_expenses(self):
        context_vals = self._get_default_expense_sheet_values()
        action_values = {
            'name': _('New Expense Reports'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.expense.sheet',
        }
        if len(context_vals) > 1:
            sheets = self.env['hr.expense.sheet'].create(context_vals)
            action_values.update({
                'views': [[False, "list"], [False, "form"]],
                'domain': [('id', 'in', sheets.ids)],
                'context': self.env.context,
            })
        else:
            context_vals_def = {}
            for key in context_vals[0]:
                context_vals_def['default_' + key] = context_vals[0][key]
            action_values.update({
                'views': [[False, "form"]],
                'target': 'current',
                'context': {f'default_{key}': value for key, value in context_vals[0].items()},
            })
        return action_values

    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window']._for_xml_id('base.action_attachment')
        res['domain'] = [('res_model', '=', 'hr.expense'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'hr.expense', 'default_res_id': self.id}
        return res

    def action_approve_duplicates(self):
        root = self.env['ir.model.data']._xmlid_to_res_id("base.partner_root")
        for expense in self.duplicate_expense_ids:
            expense.message_post(
                body=_('%(user)s confirms this expense is not a duplicate with similar expense.', user=self.env.user.name),
                author_id=root
            )

    def _get_split_values(self):
        self.ensure_one()
        half_price = self.total_amount / 2
        price_round_up = float_round(half_price, precision_digits=2, rounding_method='UP')
        price_round_down = float_round(half_price, precision_digits=2, rounding_method='DOWN')

        return [{
            'name': self.name,
            'product_id': self.product_id.id,
            'total_amount': price,
            'tax_ids': self.tax_ids.ids,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'analytic_distribution': self.analytic_distribution,
            'employee_id': self.employee_id.id,
            'expense_id': self.id,
        } for price in [price_round_up, price_round_down]]

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

    def _prepare_payments_vals(self):
        self.ensure_one()

        journal = self.sheet_id.journal_id
        payment_method_line = self.env['account.payment.method.line'].search(
            [('payment_type', '=', 'outbound'),
             ('journal_id', '=', journal.id),
             ('code', '=', 'manual'),
             ('company_id', '=', self.company_id.id)], limit=1)
        if not payment_method_line:
            raise UserError(_("You need to add a manual payment method on the journal (%s)", journal.name))
        move_lines = []
        # Due to rounding and conversion mismatch between vendor bills and payments, we have to force the computation into company account
        tax_data = self.env['account.tax']._compute_taxes([
            self._convert_to_tax_base_line_dict(price_unit=self.total_amount, currency=self.currency_id)
        ])
        rate = abs(self.total_amount / self.total_amount_company) if self.total_amount_company else 1.0
        base_line_data, to_update = tax_data['base_lines_to_update'][0]  # Add base line
        amount_currency = to_update['price_subtotal']
        expense_name = self.name.split("\n")[0][:64]
        base_move_line = {
            'name': f'{self.employee_id.name}: {expense_name}',
            'account_id': base_line_data['account'].id,
            'product_id': base_line_data['product'].id,
            'analytic_distribution': base_line_data['analytic_distribution'],
            'expense_id': self.id,
            'tax_ids': [Command.set(self.tax_ids.ids)],
            'tax_tag_ids': to_update['tax_tag_ids'],
            'amount_currency': amount_currency,
            'currency_id': self.currency_id.id,
        }
        move_lines.append(base_move_line)
        total_tax_line_balance = 0.0
        for tax_line_data in tax_data['tax_lines_to_add']:  # Add tax lines
            tax_line_balance = self.company_currency_id.round(tax_line_data['tax_amount'] / rate)
            total_tax_line_balance += tax_line_balance
            tax_line = {
                'name': self.env['account.tax'].browse(tax_line_data['tax_id']).name,
                'account_id': tax_line_data['account_id'],
                'analytic_distribution': tax_line_data['analytic_distribution'],
                'expense_id': self.id,
                'tax_tag_ids': tax_line_data['tax_tag_ids'],
                'balance': tax_line_balance,
                'amount_currency': tax_line_data['tax_amount'],
                'tax_base_amount': self.company_currency_id.round(tax_line_data['base_amount'] / rate),
                'currency_id': self.currency_id.id,
                'tax_repartition_line_id': tax_line_data['tax_repartition_line_id'],
            }
            move_lines.append(tax_line)
        base_move_line['balance'] = self.total_amount_company - total_tax_line_balance
        expense_name = self.name.split("\n")[0][:64]
        move_lines.append({  # Add outstanding payment line
            'name': f'{self.employee_id.name}: {expense_name}',
            'account_id': self.sheet_id._get_expense_account_destination(),
            'balance': -self.total_amount_company,
            'amount_currency': self.currency_id.round(-self.total_amount),
            'currency_id': self.currency_id.id,
        })
        return {
            **self.sheet_id._prepare_move_vals(),
            'ref': self.name,
            'journal_id': journal.id,
            'move_type': 'entry',
            'amount': self.total_amount,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'payment_method_line_id': payment_method_line.id,
            'currency_id': self.currency_id.id,
            'line_ids': [Command.create(line) for line in move_lines],
            'attachment_ids': [
                Command.create(attachment.copy_data({'res_model': 'account.move', 'res_id': False, 'raw': attachment.raw})[0])
                for attachment in self.message_main_attachment_id]
        }

    def _prepare_move_lines_vals(self):
        self.ensure_one()
        account = self.account_id
        if not account:
            # We need to do this as the installation process may delete the original account and it doesn't recompute properly after.
            # This forces the default values if none is found
            if self.product_id:
                account = self.product_id.product_tmpl_id._get_product_accounts()['expense']
            else:
                account = self.env['ir.property']._get('property_account_expense_categ_id', 'product.category')
        expense_name = self.name.split('\n')[0][:64]
        return {
            'name': f'{self.employee_id.name}: {expense_name}',
            'account_id': account.id,
            'quantity': self.quantity or 1,
            'price_unit': self.unit_amount,
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
                'tooltip': _("Expenses that need to be submitted to the approver."),
                'currency': self.env.company.currency_id.id,
            },
            'submitted': {
                'description': _('under validation'),
                'amount': 0.0,
                'tooltip': _("Expenses from which the report has been submitted to the approver and is waiting for approval."),
                'currency': self.env.company.currency_id.id,
            },
            'approved': {
                'description': _('to be reimbursed'),
                'amount': 0.0,
                'tooltip': _("Expenses paid by employee that are approved but not paid yet."),
                'currency': self.env.company.currency_id.id,
            }
        }
        if not self.env.user.employee_ids:
            return expense_state
        target_currency = self.env.company.currency_id
        expenses = self._read_group(
            [
                ('employee_id', 'in', self.env.user.employee_ids.ids),
                # Counting the expenses to display in the dashboard:
                # - To submit: contains the expenses paid either by the employee or by the company, and that are draft or reported
                # - Under validation: contains expenses paid by the employee or paid by the company, and that have been submitted but still need to be approved/refused
                # - To be reimbursed: contains ONLY expenses paid by the employee that are approved, the payment has not yet been made
                '|',
                '&', ('payment_mode', 'in', ('own_account', 'company_account')),
                     ('state', 'in', ('draft', 'reported', 'submitted')),
                '&', ('payment_mode', '=', 'own_account'),
                     ('state', '=', 'approved')
            ], ['state', 'currency_id'], ['total_amount:sum'])
        for state, currency, total_amount_sum in expenses:
            if state in {'draft', 'reported'}:  # Fusion the two states into only one "To Submit" state
                state = 'to_submit'
            currency = currency or target_currency
            amount = currency._convert(total_amount_sum, target_currency, self.env.company, fields.Date.today())
            expense_state[state]['amount'] += amount
        return expense_state

    # ----------------------------------------
    # Mail Thread
    # ----------------------------------------

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        email_address = email_split(msg_dict.get('email_from', False))[0]

        employee = self.env['hr.employee'].search([
            '|',
            ('work_email', 'ilike', email_address),
            ('user_id.email', 'ilike', email_address)
        ], limit=1)

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
            'total_amount': price,
            'product_id': product.id if product else None,
            'product_uom_id': product.uom_id.id,
            'tax_ids': [(4, tax.id, False) for tax in product.supplier_taxes_id.filtered(lambda r: r.company_id == company)],
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
            symbols.append(re.escape(currency.symbol))
            symbols.append(re.escape(currency.name))
        symbols_pattern = '|'.join(symbols)
        price_pattern = r'((%s)?\s?%s\s?(%s)?)' % (symbols_pattern, float_pattern, symbols_pattern)
        matches = re.findall(price_pattern, expense_description)
        currency = currencies and currencies[0]
        if matches:
            match = max(matches, key=lambda match: len([group for group in match if group])) # get the longuest match. e.g. "2 chairs 120$" -> the price is 120$, not 2
            full_str = match[0]
            currency_str = match[1] or match[3]
            price = match[2].replace(',', '.')

            if currency_str and currencies:
                currencies = currencies.filtered(lambda c: currency_str in [c.symbol, c.name])
                currency = (currencies and currencies[0]) or currency
            expense_description = expense_description.replace(full_str, ' ') # remove price from description
            expense_description = re.sub(' +', ' ', expense_description.strip())

        price = float(price)
        return price, currency, expense_description

    @api.model
    def _parse_expense_subject(self, expense_description, currencies):
        """ Fetch product, price and currency info from mail subject.

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

    # TODO: Make api.multi
    def _send_expense_success_mail(self, msg_dict, expense):
        mail_template_id = 'hr_expense.hr_expense_template_register' if expense.employee_id.user_id else 'hr_expense.hr_expense_template_register_no_user'
        rendered_body = self.env['ir.qweb']._render(mail_template_id, {'expense': expense})
        body = self.env['mail.render.mixin']._replace_local_links(rendered_body)
        # TDE TODO: seems louche, check to use notify
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


class HrExpenseSheet(models.Model):
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
        Post        Anybody                 State = approve and journal_id defined
        Done        Anybody                 State = approve and journal_id defined
        Cancel      Officer                 Not his own and he is expense manager of the employee, manager of the employee
                                             or the employee is in the department managed by the officer
                    Manager                 Always
        =================================================================================
    """
    _name = "hr.expense.sheet"
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin']
    _description = "Expense Report"
    _order = "accounting_date desc, id desc"
    _check_company_auto = True

    @api.model
    def _default_employee_id(self):
        return self.env.user.employee_id

    @api.model
    def _default_journal_id(self):
        """ The journal is determining the company of the accounting entries generated from expense. We need to force journal company and expense sheet company to be the same. """
        company_journal_id = self.env.company.expense_journal_id
        if company_journal_id:
            return company_journal_id.id
        default_company_id = self.default_get(['company_id'])['company_id']
        journal = self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(default_company_id),
            ('type', '=', 'purchase'),
        ], limit=1)
        return journal.id

    name = fields.Char('Expense Report Summary', required=True, tracking=True)
    expense_line_ids = fields.One2many('hr.expense', 'sheet_id', string='Expense Lines', copy=False)
    product_ids = fields.Many2many(
        'product.product',
        string='Categories',
        compute='_compute_product_ids',
        search='_search_product_ids',
        check_company=True,
    )
    expense_number = fields.Integer(compute='_compute_expense_number', string='Number of Expenses')
    nb_account_move = fields.Integer(
        string='Number of Journal Entries',
        compute='_compute_nb_account_move',
    )
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('submit', 'Submitted'),
        ('approve', 'Approved'),
        ('post', 'Posted'),
        ('done', 'Done'),
        ('cancel', 'Refused')
    ], compute='_compute_state', string='Status', index=True, readonly=True, store=True, tracking=True, copy=False, default='draft', required=True)
    approval_state = fields.Selection([
        ('submit', 'Submitted'),
        ('approve', 'Approved'),
        ('cancel', 'Refused'),
    ], copy=False)
    approval_date = fields.Datetime('Approval Date', readonly=True)

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    company_currency_id = fields.Many2one(comodel_name='res.currency', string="Report Company Currency", related='company_id.currency_id')
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, tracking=True, default=_default_employee_id, check_company=True, domain=[('filter_for_expense', '=', True)])
    address_id = fields.Many2one('res.partner', compute='_compute_from_employee_id', store=True, readonly=False, copy=True, string="Employee Home Address", check_company=True)
    department_id = fields.Many2one('hr.department', compute='_compute_from_employee_id', store=True, readonly=False, copy=False, string='Department')
    user_id = fields.Many2one('res.users', 'Manager', compute='_compute_from_employee_id', store=True, readonly=False, copy=False, tracking=True, domain=lambda self: [('groups_id', 'in', self.env.ref('hr_expense.group_hr_expense_team_approver').id)])

    # === Amount fields === #
    total_amount = fields.Monetary('Total', currency_field='company_currency_id', compute='_compute_amount', store=True, tracking=True)
    untaxed_amount = fields.Monetary('Untaxed Amount', currency_field='company_currency_id', compute='_compute_amount', store=True)
    total_amount_taxes = fields.Monetary('Taxes', currency_field='company_currency_id', compute='_compute_amount', store=True)
    amount_residual = fields.Monetary(string="Amount Due", currency_field='company_currency_id',
        compute='_compute_from_account_move_ids', store=True)

    currency_id = fields.Many2one('res.currency', string='Currency', compute='_compute_currency_id', store=True, readonly=False)
    is_multiple_currency = fields.Boolean("Handle lines with different currencies", compute='_compute_is_multiple_currency')

    # === Account fields === #
    payment_state = fields.Selection(
        selection=lambda self: self.env["account.move"]._fields["payment_state"].selection,
        string="Payment Status",
        copy=False,
        tracking=True,
        store=True, readonly=True, compute='_compute_from_account_move_ids')
    payment_mode = fields.Selection(
        string="Paid By",
        tracking=True,
        related='expense_line_ids.payment_mode', readonly=True)
    employee_journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        check_company=True,
        domain="[('type', '=', 'purchase')]",
        default=_default_journal_id,
        help="The journal used when the expense is paid by employee.",
    )
    selectable_payment_method_line_ids = fields.Many2many('account.payment.method.line', compute='_compute_selectable_payment_method_line_ids')
    payment_method_line_id = fields.Many2one(
        comodel_name='account.payment.method.line',
        string="Payment Method",
        domain="[('id', 'in', selectable_payment_method_line_ids)]",
        compute='_compute_payment_method_line_id',
        store=True,
        readonly=False,
        help="The payment method used when the expense is paid by the company.",
    )
    accounting_date = fields.Date(
        string='Accounting Date',
        compute='_compute_accounting_date',
        store=True
    )
    account_move_ids = fields.One2many('account.move', 'expense_sheet_id', string='Journal Entries', readonly=True)
    journal_id = fields.Many2one(
        'account.journal',
        compute='_compute_journal_id',
        string="Expense Journal",
        store=True,
        check_company=True,
    )

    # === Security fields === #
    can_reset = fields.Boolean('Can Reset', compute='_compute_can_reset')
    can_approve = fields.Boolean('Can Approve', compute='_compute_can_approve')
    cannot_approve_reason = fields.Char('Cannot Approve Reason', compute='_compute_can_approve')
    is_editable = fields.Boolean("Expense Lines Are Editable By Current User", compute='_compute_is_editable')

    _sql_constraints = [
        ('journal_id_required_posted', "CHECK((state IN ('post', 'done') AND journal_id IS NOT NULL) OR (state NOT IN ('post', 'done')))", 'The journal must be set on posted expense'),
    ]

    @api.depends('expense_line_ids.total_amount_company', 'expense_line_ids.amount_tax_company')
    def _compute_amount(self):
        for sheet in self:
            sheet.total_amount = sum(sheet.expense_line_ids.mapped('total_amount_company'))
            sheet.total_amount_taxes = sum(sheet.expense_line_ids.mapped('amount_tax_company'))
            sheet.untaxed_amount = sheet.total_amount - sheet.total_amount_taxes

    @api.depends('account_move_ids.payment_state', 'account_move_ids.amount_residual')
    def _compute_from_account_move_ids(self):
        for sheet in self:
            if sheet.payment_mode == 'company_account':
                if sheet.account_move_ids:
                    # when the sheet is paid by the company, the state/amount of the related account_move_ids are not relevant
                    # unless all moves have been reversed
                    sheet.amount_residual = 0.
                    if  sheet.account_move_ids - sheet.account_move_ids.filtered('reversal_move_id'):
                        sheet.payment_state = 'paid'
                    else:
                        sheet.payment_state = 'reversed'
                else:
                    sheet.amount_residual = sum(sheet.account_move_ids.mapped('amount_residual'))
                    payment_states = set(sheet.account_move_ids.mapped('payment_state'))
                    if len(payment_states) <= 1:  # If only 1 move or only one state
                        sheet.payment_state = payment_states.pop() if payment_states else 'not_paid'
                    elif 'partial' in payment_states or 'paid' in payment_states:  # else if any are (partially) paid
                        sheet.payment_state = 'partial'
                    else:
                        sheet.payment_state = 'not_paid'
            else:
                # Only one move is created when the expenses are paid by the employee
                if sheet.account_move_ids:
                    sheet.amount_residual = sum(sheet.account_move_ids.mapped('amount_residual'))
                    sheet.payment_state = sheet.account_move_ids[:1].payment_state
                else:
                    sheet.amount_residual = 0.0
                    sheet.payment_state = 'not_paid'

    @api.depends('selectable_payment_method_line_ids')
    def _compute_payment_method_line_id(self):
        for sheet in self:
            sheet.payment_method_line_id = sheet.selectable_payment_method_line_ids._origin[:1]

    @api.depends('employee_journal_id', 'payment_method_line_id')
    def _compute_journal_id(self):
        for sheet in self:
            sheet.journal_id = sheet.payment_method_line_id.journal_id if sheet.payment_mode == 'company_account'\
                    else sheet.employee_journal_id

    @api.depends('company_id')
    def _compute_selectable_payment_method_line_ids(self):
        for sheet in self:
            sheet.selectable_payment_method_line_ids = sheet.company_id.company_expense_allowed_payment_method_line_ids\
                or self.env['account.payment.method.line'].search([('payment_type', '=', 'outbound'), ('company_id', '=', sheet.company_id.id)])

    @api.depends('account_move_ids', 'payment_state', 'approval_state')
    def _compute_state(self):
        for sheet in self:
            if sheet.payment_state != 'not_paid':
                sheet.state = 'done'
            elif sheet.account_move_ids:
                sheet.state = 'post'
            elif sheet.approval_state:
                sheet.state = sheet.approval_state
            else:
                sheet.state = 'draft'

    @api.depends('expense_line_ids.currency_id', 'company_currency_id')
    def _compute_currency_id(self):
        for sheet in self:
            if not sheet.expense_line_ids or sheet.is_multiple_currency or sheet.payment_mode == 'own_account':
                sheet.currency_id = sheet.company_currency_id
            else:
                sheet.currency_id = sheet.expense_line_ids[0].currency_id

    @api.depends('expense_line_ids.currency_id')
    def _compute_is_multiple_currency(self):
        for sheet in self:
            sheet.is_multiple_currency = len(sheet.expense_line_ids.mapped('currency_id')) > 1

    @api.depends('employee_id')
    def _compute_can_reset(self):
        is_expense_user = self.user_has_groups('hr_expense.group_hr_expense_team_approver')
        for sheet in self:
            sheet.can_reset = is_expense_user if is_expense_user else sheet.employee_id.user_id == self.env.user

    @api.depends_context('uid')
    @api.depends('employee_id')
    def _compute_can_approve(self):
        is_team_approver = self.user_has_groups('hr_expense.group_hr_expense_team_approver')
        is_approver = self.user_has_groups('hr_expense.group_hr_expense_user')
        is_hr_admin = self.user_has_groups('hr_expense.group_hr_expense_manager')

        for sheet in self:
            reason = False
            if not is_team_approver:
                reason = _("%s: Your are not a Manager or HR Officer", sheet.name)

            elif not is_hr_admin:
                current_managers = sheet.employee_id.expense_manager_id | sheet.employee_id.parent_id.user_id | sheet.employee_id.department_id.manager_id.user_id | sheet.user_id

                if self.employee_id.user_id == self.env.user:
                    reason = _("%s: It is your own expense", sheet.name)

                elif not self.env.user in current_managers and not is_approver and sheet.employee_id.expense_manager_id != self.env.user:
                    reason = _("%s: It is not from your department", sheet.name)

            sheet.can_approve = not reason
            sheet.cannot_approve_reason = reason

    @api.depends('expense_line_ids')
    def _compute_expense_number(self):
        read_group_result = self.env['hr.expense']._read_group([('sheet_id', 'in', self.ids)], ['sheet_id'], ['__count'])
        result = {sheet.id: count for sheet, count in read_group_result}
        for sheet in self:
            sheet.expense_number = result.get(sheet.id, 0)

    @api.depends('account_move_ids')
    def _compute_nb_account_move(self):
        for sheet in self:
            sheet.nb_account_move = len(sheet.account_move_ids)

    @api.depends('account_move_ids.date')
    def _compute_accounting_date(self):
        for sheet in self:
            sheet.accounting_date = sheet.account_move_ids[:1].date

    @api.depends('employee_id', 'employee_id.department_id')
    def _compute_from_employee_id(self):
        for sheet in self:
            sheet.address_id = sheet.employee_id.sudo().work_contact_id
            sheet.department_id = sheet.employee_id.department_id
            sheet.user_id = sheet.employee_id.expense_manager_id or sheet.employee_id.parent_id.user_id

    @api.depends_context('uid')
    @api.depends('employee_id', 'user_id', 'state')
    def _compute_is_editable(self):
        is_manager = self.user_has_groups('hr_expense.group_hr_expense_manager')
        is_approver = self.user_has_groups('hr_expense.group_hr_expense_user')
        for report in self:
            # Employee can edit his own expense in draft only
            is_editable = (report.employee_id.user_id == self.env.user and report.state == 'draft') or (is_manager and report.state in ['draft', 'submit', 'approve'])
            if not is_editable and report.state in ['draft', 'submit', 'approve']:
                # expense manager can edit, unless it's own expense
                current_managers = report.employee_id.expense_manager_id | report.employee_id.parent_id.user_id | report.employee_id.department_id.manager_id.user_id | report.user_id
                is_editable = (is_approver or self.env.user in current_managers) and report.employee_id.user_id != self.env.user
            report.is_editable = is_editable

    @api.constrains('expense_line_ids')
    def _check_payment_mode(self):
        for sheet in self:
            expense_lines = sheet.mapped('expense_line_ids')
            if expense_lines and any(expense.payment_mode != expense_lines[0].payment_mode for expense in expense_lines):
                raise ValidationError(_("All expenses in an expense report must have the same \"paid by\" criteria."))

    @api.depends('expense_line_ids')
    def _compute_product_ids(self):
        for sheet in self:
            sheet.product_ids = sheet.expense_line_ids.mapped('product_id')

    @api.constrains('expense_line_ids', 'employee_id')
    def _check_employee(self):
        for sheet in self:
            employee_ids = sheet.expense_line_ids.mapped('employee_id')
            if len(employee_ids) > 1 or (len(employee_ids) == 1 and employee_ids != sheet.employee_id):
                raise ValidationError(_('You cannot add expenses of another employee.'))

    @api.constrains('expense_line_ids', 'company_id')
    def _check_expense_lines_company(self):
        for sheet in self:
            if any(expense.company_id != sheet.company_id for expense in sheet.expense_line_ids):
                raise ValidationError(_('An expense report must contain only lines from the same company.'))

    def _search_product_ids(self, operator, value):
        if operator == 'in' and not isinstance(value, list):
            value = [value]
        return [('expense_line_ids.product_id', operator, value)]

    # ----------------------------------------
    # ORM Overrides
    # ----------------------------------------

    def _read_format(self, fnames, load='_classic_read'):
        # setting the context in the field on the view is not enough
        self = self.with_context(show_payment_journal_id=True)
        return super()._read_format(fnames, load)

    @api.model_create_multi
    def create(self, vals_list):
        context = clean_context(self.env.context)
        context.update({
            'mail_create_nosubscribe': True,
            'mail_auto_subscribe_no_notify': True
        })
        sheets = super(HrExpenseSheet, self.with_context(context)).create(vals_list)
        sheets.activity_update()
        return sheets

    @api.ondelete(at_uninstall=False)
    def _unlink_except_posted_or_paid(self):
        for expense in self:
            if expense.state in ['post', 'done']:
                raise UserError(_('You cannot delete a posted or paid expense.'))

    # --------------------------------------------
    # Mail Thread
    # --------------------------------------------

    def _get_mail_thread_data_attachments(self):
        """
        In order to see in the sheet attachment preview the corresponding
        expenses' attachments, the latter attachments are added to the fetched data for the sheet record.
        """
        self.ensure_one()
        res = super()._get_mail_thread_data_attachments()
        expense_ids = self.expense_line_ids
        expense_attachments = self.env['ir.attachment'].search([('res_id', 'in', expense_ids.ids), ('res_model', '=', 'hr.expense')], order='id desc')
        return res | expense_attachments

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'draft':
            return self.env.ref('hr_expense.mt_expense_reset')
        if 'state' in init_values and self.state == 'approve':
            if init_values['state'] in ('post', 'done'):
                return self.env.ref('hr_expense.mt_expense_entry_delete')
            return self.env.ref('hr_expense.mt_expense_approved')
        if 'state' in init_values and self.state == 'cancel':
            return self.env.ref('hr_expense.mt_expense_refused')
        if 'state' in init_values and self.state == 'done':
            return self.env.ref('hr_expense.mt_expense_paid')
        return super()._track_subtype(init_values)

    def _message_auto_subscribe_followers(self, updated_values, subtype_ids):
        res = super()._message_auto_subscribe_followers(updated_values, subtype_ids)
        if updated_values.get('employee_id'):
            employee = self.env['hr.employee'].browse(updated_values['employee_id'])
            if employee.user_id:
                res.append((employee.user_id.partner_id.id, subtype_ids, False))
        return res

    def activity_update(self):
        reports_requiring_feedback = self.env['hr.expense.sheet']
        reports_activity_unlink = self.env['hr.expense.sheet']
        for expense_report in self:
            if expense_report.state == 'submit':
                expense_report.activity_schedule(
                    'hr_expense.mail_act_expense_approval',
                    user_id=expense_report.sudo()._get_responsible_for_approval().id or self.env.user.id)
            elif expense_report.state == 'approve':
                reports_requiring_feedback |= expense_report
            elif expense_report.state in ('draft', 'cancel'):
                reports_activity_unlink |= expense_report
        if reports_requiring_feedback:
            reports_requiring_feedback.activity_feedback(['hr_expense.mail_act_expense_approval'])
        if reports_activity_unlink:
            reports_activity_unlink.activity_unlink(['hr_expense.mail_act_expense_approval'])

    # --------------------------------------------
    # Actions
    # --------------------------------------------

    def action_submit_sheet(self):
        self._do_submit()

    def action_approve_expense_sheets(self):
        self._check_can_approve()
        self._validate_analytic_distribution()
        duplicates = self.expense_line_ids.duplicate_expense_ids.filtered(lambda exp: exp.state in ['approved', 'done'])
        if duplicates:
            action = self.env["ir.actions.act_window"]._for_xml_id('hr_expense.hr_expense_approve_duplicate_action')
            action['context'] = {'default_sheet_ids': self.ids, 'default_expense_ids': duplicates.ids}
            return action
        self._do_approve()

    def action_refuse_expense_sheets(self):
        self._check_can_refuse()
        action = self.env["ir.actions.act_window"]._for_xml_id('hr_expense.hr_expense_refuse_wizard_action')
        return action

    def action_reset_approval_expense_sheets(self):
        self._check_can_reset_approval()
        self._do_reset_approval()

    def action_sheet_move_create(self):
        self._check_can_create_move()
        self._do_create_moves()

    def action_reset_expense_sheets(self):
        self._do_reverse_moves()
        self._do_reset_approval()

    def action_register_payment(self):
        ''' Open the account.payment.register wizard to pay the selected journal entries.
        There can be more than one bank_account_id in the expense sheet when registering payment for multiple expenses.
        The default_partner_bank_id is set only if there is one available, if more than one the field is left empty.
        :return: An action opening the account.payment.register wizard.
        '''
        return self.account_move_ids.with_context(
                default_partner_bank_id=self.employee_id.sudo().bank_account_id.id if len(self.employee_id.sudo().bank_account_id.ids) <= 1 else None,
            ).action_register_payment()

    def action_open_expense_view(self):
        self.ensure_one()
        return {
            'name': _('Expenses'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'views': [[False, "list"], [False, "form"]],
            'res_model': 'hr.expense',
            'domain': [('id', 'in', self.expense_line_ids.ids)],
        }

    def action_open_account_moves(self):
        self.ensure_one()
        if self.payment_mode == 'own_account':
            res_model = 'account.move'
            record_ids = self.account_move_ids
        else:
            res_model = 'account.payment'
            record_ids = self.account_move_ids.mapped('payment_id')

        action = {'type': 'ir.actions.act_window', 'res_model': res_model}
        if len(self.account_move_ids) == 1:
            action.update({
                'name': record_ids.name,
                'view_mode': 'form',
                'res_id': record_ids.id,
                'views': [(False, 'form')],
            })
        else:
            action.update({
                'name': _("Journal entries"),
                'view_mode': 'list',
                'domain': [('id', 'in', record_ids.ids)],
                'views': [(False, 'list'), (False, 'form')],
            })
        return action

    # --------------------------------------------
    # Business
    # --------------------------------------------

    def set_to_paid(self):
        # hook used in other modules to bypass payment registration
        self.write({'state': 'done'})

    def set_to_posted(self):
        # hook used in other modules to bypass move creation
        self.write({'state': 'post'})

    def _check_can_approve(self):
        if not all(self.mapped('can_approve')):
            reasons = _("You cannot approve:\n %s", "\n".join(self.mapped('cannot_approve_reason')))
            raise UserError(reasons)

    def _check_can_refuse(self):
        if not all(self.mapped('can_approve')):
            reasons = _("You cannot refuse:\n %s", "\n".join(self.mapped('cannot_approve_reason')))
            raise UserError(reasons)

    def _check_can_reset_approval(self):
        if not all(self.mapped('can_reset')):
            raise UserError(_("Only HR Officers or the concerned employee can reset to draft."))

    def _check_can_create_move(self):
        if any(sheet.state != 'approve' for sheet in self):
            raise UserError(_("You can only generate accounting entry for approved expense(s)."))

        if any(not sheet.journal_id for sheet in self):
            raise UserError(_("Specify expense journal to generate accounting entries."))

        if not self.employee_id.work_email:
            raise UserError(_("The work email of the employee is required to post the expense report. Please add it on the employee form."))

    def _do_submit(self):
        self.write({'approval_state': 'submit'})
        self.sudo().activity_update()

    def _do_approve(self):
        for sheet in self.filtered(lambda s: s.state in ['submit', 'draft']):
            sheet.write({
                'approval_state': 'approve',
                'user_id': sheet.user_id.id or self.env.user.id,
                'approval_date': fields.Date.context_today(sheet),
            })
        self.activity_update()

    def _do_reset_approval(self):
        self.sudo().write({
            'approval_state': False,
        })
        self.activity_update()

    def _do_refuse(self, reason):
        self.write({'state': 'cancel'})
        subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment')
        for sheet in self:
            sheet.message_post_with_source(
                'hr_expense.hr_expense_template_refuse_reason',
                subtype_id=subtype_id,
                render_values={'reason': reason, 'name': sheet.name},
            )
        self.activity_update()

    def _do_create_moves(self):
        self = self.with_context(clean_context(self.env.context)) # remove default_*
        skip_context = {
            'skip_invoice_sync':True,
            'skip_invoice_line_sync':True,
            'skip_account_move_synchronization':True,
            'check_move_validity':False,
        }
        own_account_sheets = self.filtered(lambda sheet: sheet.payment_mode == 'own_account')
        company_account_sheets = self - own_account_sheets

        moves = self.env['account.move'].create([sheet._prepare_bills_vals() for sheet in own_account_sheets])
        payments = self.env['account.payment'].with_context(**skip_context).create([expense._prepare_payments_vals() for expense in company_account_sheets.expense_line_ids])
        moves |= payments.move_id
        moves.action_post()
        self.activity_update()

        return moves

    def _do_reverse_moves(self):
        draft_moves = self.account_move_ids.filtered(lambda _move: _move.state == 'draft')
        draft_moves.unlink()
        moves = self.account_move_ids - draft_moves
        moves._reverse_moves(default_values_list=[{'invoice_date': fields.Date.context_today(move), 'ref': False} for move in moves], cancel=True)

    def _prepare_bills_vals(self):
        self.ensure_one()
        return {
            **self._prepare_move_vals(),
            'invoice_date': self.accounting_date or fields.Date.context_today(self),
            'journal_id': self.journal_id.id,
            'ref': self.name,
            'move_type': 'in_invoice',
            'partner_id': self.employee_id.sudo().work_contact_id.id,
            'currency_id': self.currency_id.id,
            'line_ids': [Command.create(expense._prepare_move_lines_vals()) for expense in self.expense_line_ids],
            'attachment_ids': [
                Command.create(attachment.copy_data({'res_model': 'account.move', 'res_id': False, 'raw': attachment.raw})[0])
                for attachment in self.expense_line_ids.message_main_attachment_id
            ],
        }

    def _prepare_move_vals(self):
        self.ensure_one()
        return {
            # force the name to the default value, to avoid an eventual 'default_name' in the context
            # to set it to '' which cause no number to be given to the account.move when posted.
            'name': '/',
            'date': self.accounting_date or max(self.expense_line_ids.mapped('date')) or fields.Date.context_today(self),
            'expense_sheet_id': self.id,
        }

    def _validate_analytic_distribution(self):
        for line in self.expense_line_ids:
            line._validate_distribution(**{
                'account': line.account_id.id,
                'business_domain': 'expense',
                'company_id': line.company_id.id,
            })

    def _get_responsible_for_approval(self):
        if self.user_id:
            return self.user_id
        if self.employee_id.parent_id.user_id:
            return self.employee_id.parent_id.user_id
        if self.employee_id.department_id.manager_id.user_id:
            return self.employee_id.department_id.manager_id.user_id
        return self.env['res.users']

    def _get_expense_account_destination(self):
        self.ensure_one()
        if self.payment_mode == 'company_account':
            journal = self.payment_method_line_id.journal_id
            account_dest = (
                journal.outbound_payment_method_line_ids[:1].payment_account_id
                or journal.company_id.account_journal_payment_credit_account_id
            )
        else:
            if not self.employee_id.sudo().work_contact_id:
                raise UserError(_("No work contact found for the employee %s, please configure one.") % (self.employee_id.name))
            partner = self.employee_id.sudo().work_contact_id.with_company(self.company_id)
            account_dest = partner.property_account_payable_id or partner.parent_id.property_account_payable_id
        return account_dest.id
