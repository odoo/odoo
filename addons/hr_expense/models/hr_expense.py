# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from markupsafe import Markup
from odoo import api, fields, Command, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import email_split, float_is_zero, float_repr
from odoo.tools.misc import clean_context, format_date
from odoo.addons.account.models.account_move import PAYMENT_STATE_SELECTION


class HrExpense(models.Model):

    _name = "hr.expense"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Expense"
    _order = "date desc, id desc"
    _check_company_auto = True

    @api.model
    def _default_employee_id(self):
        employee = self.env.user.employee_id
        if not employee and not self.env.user.has_group('hr_expense.group_hr_expense_team_approver'):
            raise ValidationError(_('The current user has no related employee. Please, create one.'))
        return employee

    @api.model
    def _default_product_uom_id(self):
        return self.env['uom.uom'].search([], limit=1, order='id')

    @api.model
    def _default_account_id(self):
        return self.env['ir.property']._get('property_account_expense_categ_id', 'product.category')

    @api.model
    def _get_employee_id_domain(self):
        res = [('id', '=', 0)] # Nothing accepted by domain, by default
        if self.user_has_groups('hr_expense.group_hr_expense_user') or self.user_has_groups('account.group_account_user'):
            res = "['|', ('company_id', '=', False), ('company_id', '=', company_id)]"  # Then, domain accepts everything
        elif self.user_has_groups('hr_expense.group_hr_expense_team_approver') and self.env.user.employee_ids:
            user = self.env.user
            employee = self.env.user.employee_id
            res = [
                '|', '|', '|',
                ('department_id.manager_id', '=', employee.id),
                ('parent_id', '=', employee.id),
                ('id', '=', employee.id),
                ('expense_manager_id', '=', user.id),
                '|', ('company_id', '=', False), ('company_id', '=', employee.company_id.id),
            ]
        elif self.env.user.employee_id:
            employee = self.env.user.employee_id
            res = [('id', '=', employee.id), '|', ('company_id', '=', False), ('company_id', '=', employee.company_id.id)]
        return res

    name = fields.Char('Description', compute='_compute_from_product_id_company_id', store=True, required=True, copy=True,
        states={'draft': [('readonly', False)], 'reported': [('readonly', False)], 'approved': [('readonly', False)], 'refused': [('readonly', False)]})
    date = fields.Date(readonly=True, states={'draft': [('readonly', False)], 'reported': [('readonly', False)], 'approved': [('readonly', False)], 'refused': [('readonly', False)]}, default=fields.Date.context_today, string="Expense Date")
    accounting_date = fields.Date(string="Accounting Date", related='sheet_id.accounting_date', store=True, groups='account.group_account_invoice,account.group_account_readonly')
    employee_id = fields.Many2one('hr.employee', compute='_compute_employee_id', string="Employee",
        store=True, required=True, readonly=False, tracking=True,
        states={'approved': [('readonly', True)], 'done': [('readonly', True)]},
        default=_default_employee_id, domain=lambda self: self._get_employee_id_domain(), check_company=True)
    # product_id not required to allow create an expense without product via mail alias, but should be required on the view.
    product_id = fields.Many2one('product.product', string='Product', readonly=True, tracking=True, states={'draft': [('readonly', False)], 'reported': [('readonly', False)], 'approved': [('readonly', False)], 'refused': [('readonly', False)]}, domain="[('can_be_expensed', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]", ondelete='restrict')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', compute='_compute_from_product_id_company_id',
        store=True, copy=True, states={'draft': [('readonly', False)], 'refused': [('readonly', False)]},
        default=_default_product_uom_id, domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', readonly=True, string="UoM Category")
    unit_amount = fields.Float("Unit Price", compute='_compute_from_product_id_company_id', store=True, required=True, copy=True,
        states={'draft': [('readonly', False)], 'reported': [('readonly', False)], 'approved': [('readonly', False)], 'refused': [('readonly', False)]}, digits='Product Price')
    quantity = fields.Float(required=True, readonly=True, states={'draft': [('readonly', False)], 'reported': [('readonly', False)], 'approved': [('readonly', False)], 'refused': [('readonly', False)]}, digits='Product Unit of Measure', default=1)
    tax_ids = fields.Many2many('account.tax', 'expense_tax', 'expense_id', 'tax_id',
        compute='_compute_from_product_id_company_id', store=True, readonly=False,
        domain="[('company_id', '=', company_id), ('type_tax_use', '=', 'purchase'), ('price_include', '=', True)]", string='Taxes',
        help="The taxes should be \"Included In Price\"")
    # TODO SGV can be removed
    untaxed_amount = fields.Float("Subtotal", store=True, compute='_compute_amount_tax', digits='Account', copy=True)
    amount_residual = fields.Monetary(string='Amount Due', compute='_compute_amount_residual')
    total_amount = fields.Monetary("Total In Currency", compute='_compute_amount', store=True, currency_field='currency_id', tracking=True, readonly=False)
    company_currency_id = fields.Many2one('res.currency', string="Report Company Currency", related='company_id.currency_id', readonly=True)
    total_amount_company = fields.Monetary("Total", compute='_compute_total_amount_company', store=True, currency_field='company_currency_id')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, states={'draft': [('readonly', False)], 'refused': [('readonly', False)]}, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=False, store=True, states={'reported': [('readonly', True)], 'approved': [('readonly', True)], 'done': [('readonly', True)]}, compute='_compute_currency_id', default=lambda self: self.env.company.currency_id)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', check_company=True)
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags', states={'post': [('readonly', True)], 'done': [('readonly', True)]}, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    account_id = fields.Many2one('account.account', compute='_compute_from_product_id_company_id', store=True, readonly=False, string='Account',
        default=_default_account_id, domain="[('internal_type', '=', 'other'), ('company_id', '=', company_id)]", help="An expense account is expected")
    description = fields.Text('Notes...', readonly=True, states={'draft': [('readonly', False)], 'reported': [('readonly', False)], 'refused': [('readonly', False)]})
    payment_mode = fields.Selection([
        ("own_account", "Employee (to reimburse)"),
        ("company_account", "Company")
    ], default='own_account', tracking=True, states={'done': [('readonly', True)], 'approved': [('readonly', True)], 'reported': [('readonly', True)]}, string="Paid By")
    attachment_number = fields.Integer('Number of Attachments', compute='_compute_attachment_number')
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('reported', 'Submitted'),
        ('approved', 'Approved'),
        ('done', 'Paid'),
        ('refused', 'Refused')
    ], compute='_compute_state', string='Status', copy=False, index=True, readonly=True, store=True, default='draft', help="Status of the expense.")
    sheet_id = fields.Many2one('hr.expense.sheet', string="Expense Report", domain="[('employee_id', '=', employee_id), ('company_id', '=', company_id)]", readonly=True, copy=False)
    sheet_is_editable = fields.Boolean(compute='_compute_sheet_is_editable')
    approved_by = fields.Many2one('res.users', string='Approved By', related='sheet_id.user_id')
    approved_on = fields.Datetime(string='Approved On', related='sheet_id.approval_date')
    reference = fields.Char("Bill Reference")
    is_refused = fields.Boolean("Explicitly Refused by manager or accountant", readonly=True, copy=False)

    is_editable = fields.Boolean("Is Editable By Current User", compute='_compute_is_editable')
    is_ref_editable = fields.Boolean("Reference Is Editable By Current User", compute='_compute_is_ref_editable')
    product_has_cost =  fields.Boolean("Is product with non zero cost selected", compute='_compute_product_has_cost')
    same_currency = fields.Boolean("Is currency_id different from the company_currency_id", compute='_compute_same_currency')
    duplicate_expense_ids = fields.Many2many('hr.expense', compute='_compute_duplicate_expense_ids')

    sample = fields.Boolean()
    label_total_amount_company = fields.Char(compute='_compute_label_total_amount_company')
    label_convert_rate = fields.Char(compute='_compute_label_convert_rate')

    @api.depends("product_has_cost")
    def _compute_currency_id(self):
        for expense in self.filtered("product_has_cost"):
            expense.currency_id = expense.company_currency_id

    @api.depends_context('lang')
    @api.depends("company_currency_id")
    def _compute_label_total_amount_company(self):
        for expense in self:
            expense.label_total_amount_company = _("Total %s", expense.company_currency_id.name) if expense.company_currency_id else _("Total")

    @api.depends('currency_id', 'company_currency_id')
    def _compute_same_currency(self):
        for expense in self:
            expense.same_currency = bool(not expense.company_id or (expense.currency_id and expense.currency_id == expense.company_currency_id))

    @api.depends('product_id')
    def _compute_product_has_cost(self):
        for expense in self:
            expense.product_has_cost = bool(expense.product_id and expense.unit_amount)

    @api.depends('sheet_id', 'sheet_id.account_move_id', 'sheet_id.state')
    def _compute_state(self):
        for expense in self:
            if not expense.sheet_id or expense.sheet_id.state == 'draft':
                expense.state = "draft"
            elif expense.sheet_id.state == "cancel":
                expense.state = "refused"
            elif expense.sheet_id.state == "approve" or expense.sheet_id.state == "post":
                expense.state = "approved"
            elif not expense.sheet_id.account_move_id:
                expense.state = "reported"
            else:
                expense.state = "done"

    @api.depends('quantity', 'unit_amount', 'tax_ids', 'currency_id')
    def _compute_amount(self):
        for expense in self:
            if expense.unit_amount:
                taxes = expense.tax_ids.compute_all(expense.unit_amount, expense.currency_id, expense.quantity, expense.product_id, expense.employee_id.user_id.partner_id)
                expense.total_amount = taxes.get('total_included')

    @api.depends('total_amount', 'tax_ids', 'currency_id')
    def _compute_amount_tax(self):
        for expense in self:
            # the taxes should be "Included In Price", as the entered
            # total_amount includes all the taxes already
            # for the cases with total price, the quantity is always 1
            amount = expense.total_amount
            quantity = 1
            taxes = expense.tax_ids.compute_all(amount, expense.currency_id, quantity, expense.product_id, expense.employee_id.user_id.partner_id)
            expense.untaxed_amount = taxes.get('total_excluded')

    @api.depends("sheet_id.account_move_id.line_ids")
    def _compute_amount_residual(self):
        for expense in self:
            if not expense.sheet_id:
                expense.amount_residual = expense.total_amount
                continue
            if not expense.currency_id or expense.currency_id == expense.company_id.currency_id:
                residual_field = 'amount_residual'
            else:
                residual_field = 'amount_residual_currency'
            payment_term_lines = expense.sheet_id.account_move_id.sudo().line_ids \
                .filtered(lambda line: line.expense_id == expense and line.account_internal_type in ('receivable', 'payable'))
            expense.amount_residual = -sum(payment_term_lines.mapped(residual_field))

    @api.depends('date', 'total_amount', 'currency_id', 'company_currency_id')
    def _compute_total_amount_company(self):
        for expense in self:
            amount = 0
            if expense.same_currency:
                amount = expense.total_amount
            else:
                date_expense = expense.date or fields.Date.today()
                amount = expense.currency_id._convert(
                    expense.total_amount, expense.company_currency_id,
                    expense.company_id, date_expense)
            expense.total_amount_company = amount

    @api.depends('date', 'total_amount', 'currency_id', 'company_currency_id')
    def _compute_label_convert_rate(self):
        records_with_diff_currency = self.filtered(lambda x: not x.same_currency and x.currency_id)
        (self - records_with_diff_currency).label_convert_rate = False
        for expense in records_with_diff_currency:
            date_expense = expense.date or fields.Date.today()
            rate = expense.currency_id._get_conversion_rate(
                expense.currency_id, expense.company_currency_id, expense.company_id, date_expense)
            rate_txt = _('1 %(exp_cur)s = %(rate)s %(comp_cur)s', exp_cur=expense.currency_id.name, rate=float_repr(rate, 6), comp_cur=expense.company_currency_id.name)
            expense.label_convert_rate = rate_txt

    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].read_group([('res_model', '=', 'hr.expense'), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for expense in self:
            expense.attachment_number = attachment.get(expense._origin.id, 0)

    @api.depends('employee_id')
    def _compute_is_editable(self):
        is_account_manager = self.env.user.has_group('account.group_account_user') or self.env.user.has_group('account.group_account_manager')
        for expense in self:
            if expense.state == 'draft' or expense.sheet_id.state in ['draft', 'submit']:
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
            if expense.state == 'draft' or expense.sheet_id.state in ['draft', 'submit']:
                expense.is_ref_editable = True
            else:
                expense.is_ref_editable = is_account_manager

    @api.depends('product_id', 'company_id')
    def _compute_from_product_id_company_id(self):
        for expense in self.filtered('product_id'):
            expense = expense.with_company(expense.company_id)
            expense.name = expense.name or expense.product_id.display_name
            if not expense.attachment_number or (expense.attachment_number and not expense.unit_amount):
                expense.unit_amount = expense.product_id.price_compute('standard_price')[expense.product_id.id]
            expense.product_uom_id = expense.product_id.uom_id
            expense.tax_ids = expense.product_id.supplier_taxes_id.filtered(lambda tax: tax.price_include and tax.company_id == expense.company_id)  # taxes only from the same company
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

    @api.onchange('product_id', 'date', 'account_id')
    def _onchange_product_id_date_account_id(self):
        rec = self.env['account.analytic.default'].sudo().account_get(
            product_id=self.product_id.id,
            account_id=self.account_id.id,
            company_id=self.company_id.id,
            date=self.date
        )
        self.analytic_account_id = self.analytic_account_id or rec.analytic_id.id
        self.analytic_tag_ids = self.analytic_tag_ids or rec.analytic_tag_ids.ids

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

    def create_expense_from_attachments(self, attachment_ids=None, view_type='tree'):
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
            product = product.filtered(lambda p: p.default_code == "EXP_GEN") or product[0]
        else:
            raise UserError(_("You need to have at least one category that can be expensed in your database to proceed!"))

        for attachment in attachments:
            expense = self.env['hr.expense'].create({
                'name': attachment.name.split('.')[0],
                'unit_amount': 0,
                'product_id': product.id
            })
            attachment.write({
                'res_model': 'hr.expense',
                'res_id': expense.id,
            })
            attachment.register_as_main_attachment()
            expenses += expense
        return {
            'name': _('Generated Expenses'),
            'res_model': 'hr.expense',
            'type': 'ir.actions.act_window',
            'views': [[False, view_type], [False, "form"]],
            'context': {'search_default_my_expenses': 1, 'search_default_no_report': 1},
        }

    def attach_document(self, **kwargs):
        pass

    # ----------------------------------------
    # ORM Overrides
    # ----------------------------------------

    @api.ondelete(at_uninstall=False)
    def _unlink_except_posted_or_approved(self):
        for expense in self:
            if expense.state in ['done', 'approved']:
                raise UserError(_('You cannot delete a posted or approved expense.'))

    def write(self, vals):
        if 'tax_ids' in vals or 'analytic_account_id' in vals or 'account_id' in vals:
            if any(not expense.is_editable for expense in self):
                raise UserError(_('You are not authorized to edit this expense report.'))
        if 'reference' in vals:
            if any(not expense.is_ref_editable for expense in self):
                raise UserError(_('You are not authorized to edit the reference of this expense report.'))
        return super(HrExpense, self).write(vals)

    @api.model
    def get_empty_list_help(self, help_message):
        return super(HrExpense, self).get_empty_list_help(help_message or '' + self._get_empty_list_mail_alias())

    @api.model
    def _get_empty_list_mail_alias(self):
        use_mailgateway = self.env['ir.config_parameter'].sudo().get_param('hr_expense.use_mailgateway')
        alias_record = use_mailgateway and self.env.ref('hr_expense.mail_alias_expense') or False
        if alias_record and alias_record.alias_domain and alias_record.alias_name:
            return Markup("""
<p>
Or send your receipts at <a href="mailto:%(email)s?subject=Lunch%%20with%%20customer%%3A%%20%%2412.32">%(email)s</a>.
</p>""") % {'email': '%s@%s' % (alias_record.alias_name, alias_record.alias_domain)}
        return ""

    # ----------------------------------------
    # Actions
    # ----------------------------------------

    def action_view_sheet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.expense.sheet',
            'target': 'current',
            'res_id': self.sheet_id.id
        }

    def _get_default_expense_sheet_values(self):
        if any(expense.state != 'draft' or expense.sheet_id for expense in self):
            raise UserError(_("You cannot report twice the same line!"))
        if len(self.mapped('employee_id')) != 1:
            raise UserError(_("You cannot report expenses for different employees in the same report."))
        if any(not expense.product_id for expense in self):
            raise UserError(_("You can not create report without category."))

        todo = self.filtered(lambda x: x.payment_mode=='own_account') or self.filtered(lambda x: x.payment_mode=='company_account')
        if len(todo) == 1:
            expense_name = todo.name
        else:
            dates = todo.mapped('date')
            min_date = format_date(self.env, min(dates))
            max_date = format_date(self.env, max(dates))
            expense_name = min_date if max_date == min_date else "%s - %s" % (min_date, max_date)

        values = {
            'default_company_id': self.company_id.id,
            'default_employee_id': self[0].employee_id.id,
            'default_name': expense_name,
            'default_expense_line_ids': [Command.set(todo.ids)],
            'default_state': 'draft',
            'create': False
        }
        return values

    def action_submit_expenses(self):
        context_vals = self._get_default_expense_sheet_values()
        return {
            'name': _('New Expense Report'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.expense.sheet',
            'target': 'current',
            'context': context_vals,
        }

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

    # ----------------------------------------
    # Business
    # ----------------------------------------

    def _prepare_move_values(self):
        """
        This function prepares move values related to an expense
        """
        self.ensure_one()
        journal = self.sheet_id.bank_journal_id if self.payment_mode == 'company_account' else self.sheet_id.journal_id
        account_date = self.sheet_id.accounting_date or self.date
        move_values = {
            'journal_id': journal.id,
            'company_id': self.sheet_id.company_id.id,
            'date': account_date,
            'ref': self.sheet_id.name,
            # force the name to the default value, to avoid an eventual 'default_name' in the context
            # to set it to '' which cause no number to be given to the account.move when posted.
            'name': '/',
        }
        return move_values

    def _get_account_move_by_sheet(self):
        """ Return a mapping between the expense sheet of current expense and its account move
            :returns dict where key is a sheet id, and value is an account move record
        """
        move_grouped_by_sheet = {}
        for expense in self:
            # create the move that will contain the accounting entries
            if expense.sheet_id.id not in move_grouped_by_sheet:
                move_vals = expense._prepare_move_values()
                move = self.env['account.move'].with_context(default_journal_id=move_vals['journal_id']).create(move_vals)
                move_grouped_by_sheet[expense.sheet_id.id] = move
            else:
                move = move_grouped_by_sheet[expense.sheet_id.id]
        return move_grouped_by_sheet

    def _get_expense_account_source(self):
        self.ensure_one()
        if self.account_id:
            account = self.account_id
        elif self.product_id:
            account = self.product_id.product_tmpl_id.with_company(self.company_id)._get_product_accounts()['expense']
            if not account:
                raise UserError(
                    _("No Expense account found for the product %s (or for its category), please configure one.") % (self.product_id.name))
        else:
            account = self.env['ir.property'].with_company(self.company_id)._get('property_account_expense_categ_id', 'product.category')
            if not account:
                raise UserError(_('Please configure Default Expense account for Category expense: `property_account_expense_categ_id`.'))
        return account

    def _get_expense_account_destination(self):
        self.ensure_one()
        account_dest = self.env['account.account']
        if self.payment_mode == 'company_account':
            journal = self.sheet_id.bank_journal_id
            account_dest = (
                journal.outbound_payment_method_line_ids[0].payment_account_id
                or journal.company_id.account_journal_payment_credit_account_id
            )
        else:
            if not self.employee_id.sudo().address_home_id:
                raise UserError(_("No Home Address found for the employee %s, please configure one.") % (self.employee_id.name))
            partner = self.employee_id.sudo().address_home_id.with_company(self.company_id)
            account_dest = partner.property_account_payable_id or partner.parent_id.property_account_payable_id
        return account_dest.id

    def _get_account_move_line_values(self):
        move_line_values_by_expense = {}
        for expense in self:
            move_line_name = expense.employee_id.name + ': ' + expense.name.split('\n')[0][:64]
            account_src = expense._get_expense_account_source()
            account_dst = expense._get_expense_account_destination()
            account_date = expense.sheet_id.accounting_date or expense.date or fields.Date.context_today(expense)

            company_currency = expense.company_id.currency_id

            move_line_values = []
            unit_amount = expense.unit_amount or expense.total_amount
            quantity = expense.quantity if expense.unit_amount else 1
            taxes = expense.tax_ids.with_context(round=True).compute_all(unit_amount, expense.currency_id,quantity,expense.product_id)
            total_amount = 0.0
            total_amount_currency = 0.0
            partner_id = expense.employee_id.sudo().address_home_id.commercial_partner_id.id

            # source move line
            balance = expense.currency_id._convert(taxes['total_excluded'], company_currency, expense.company_id, account_date)
            amount_currency = taxes['total_excluded']
            move_line_src = {
                'name': move_line_name,
                'quantity': expense.quantity or 1,
                'debit': balance if balance > 0 else 0,
                'credit': -balance if balance < 0 else 0,
                'amount_currency': amount_currency,
                'account_id': account_src.id,
                'product_id': expense.product_id.id,
                'product_uom_id': expense.product_uom_id.id,
                'analytic_account_id': expense.analytic_account_id.id,
                'analytic_tag_ids': [(6, 0, expense.analytic_tag_ids.ids)],
                'expense_id': expense.id,
                'partner_id': partner_id,
                'tax_ids': [(6, 0, expense.tax_ids.ids)],
                'tax_tag_ids': [(6, 0, taxes['base_tags'])],
                'currency_id': expense.currency_id.id,
            }
            move_line_values.append(move_line_src)
            total_amount -= balance
            total_amount_currency -= move_line_src['amount_currency']

            # taxes move lines
            for tax in taxes['taxes']:
                balance = expense.currency_id._convert(tax['amount'], company_currency, expense.company_id, account_date)
                amount_currency = tax['amount']

                if tax['tax_repartition_line_id']:
                    rep_ln = self.env['account.tax.repartition.line'].browse(tax['tax_repartition_line_id'])
                    base_amount = self.env['account.move']._get_base_amount_to_display(tax['base'], rep_ln)
                    base_amount = expense.currency_id._convert(base_amount, company_currency, expense.company_id, account_date)
                else:
                    base_amount = None

                move_line_tax_values = {
                    'name': tax['name'],
                    'quantity': 1,
                    'debit': balance if balance > 0 else 0,
                    'credit': -balance if balance < 0 else 0,
                    'amount_currency': amount_currency,
                    'account_id': tax['account_id'] or move_line_src['account_id'],
                    'tax_repartition_line_id': tax['tax_repartition_line_id'],
                    'tax_tag_ids': tax['tag_ids'],
                    'tax_base_amount': base_amount,
                    'expense_id': expense.id,
                    'partner_id': partner_id,
                    'currency_id': expense.currency_id.id,
                    'analytic_account_id': expense.analytic_account_id.id if tax['analytic'] else False,
                    'analytic_tag_ids': [(6, 0, expense.analytic_tag_ids.ids)] if tax['analytic'] else False,
                }
                total_amount -= balance
                total_amount_currency -= move_line_tax_values['amount_currency']
                move_line_values.append(move_line_tax_values)

            # destination move line
            move_line_dst = {
                'name': move_line_name,
                'debit': total_amount > 0 and total_amount,
                'credit': total_amount < 0 and -total_amount,
                'account_id': account_dst,
                'date_maturity': account_date,
                'amount_currency': total_amount_currency,
                'currency_id': expense.currency_id.id,
                'expense_id': expense.id,
                'partner_id': partner_id,
                'exclude_from_invoice_tab': True,
            }
            move_line_values.append(move_line_dst)

            move_line_values_by_expense[expense.id] = move_line_values
        return move_line_values_by_expense

    def action_move_create(self):
        '''
        main function that is called when trying to create the accounting entries related to an expense
        '''
        move_group_by_sheet = self._get_account_move_by_sheet()

        move_line_values_by_expense = self._get_account_move_line_values()

        for expense in self:
            # get the account move of the related sheet
            move = move_group_by_sheet[expense.sheet_id.id]

            # get move line values
            move_line_values = move_line_values_by_expense.get(expense.id)

            # link move lines to move, and move to expense sheet
            move.write({'line_ids': [(0, 0, line) for line in move_line_values]})
            expense.sheet_id.write({'account_move_id': move.id})

            if expense.payment_mode == 'company_account':
                expense.sheet_id.paid_expense_sheets()

        # post the moves
        for move in move_group_by_sheet.values():
            move._post()

        return move_group_by_sheet

    def refuse_expense(self, reason):
        self.write({'is_refused': True})
        self.sheet_id.write({'state': 'cancel'})
        self.sheet_id.message_post_with_view('hr_expense.hr_expense_template_refuse_reason',
                                             values={'reason': reason, 'is_sheet': False, 'name': self.name})

    @api.model
    def get_expense_dashboard(self):
        expense_state = {
            'draft': {
                'description': _('to report'),
                'amount': 0.0,
                'currency': self.env.company.currency_id.id,
            },
            'reported': {
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
        expenses = self.read_group(
            [
                ('employee_id', 'in', self.env.user.employee_ids.ids),
                ('payment_mode', '=', 'own_account'),
                ('state', 'in', ['draft', 'reported', 'approved'])
            ], ['total_amount', 'currency_id', 'state'], ['state', 'currency_id'], lazy=False)
        for expense in expenses:
            state = expense['state']
            currency = self.env['res.currency'].browse(expense['currency_id'][0]) if expense['currency_id'] else target_currency
            amount = currency._convert(
                    expense['total_amount'], target_currency, self.env.company, fields.Date.today())
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
            'unit_amount': price,
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

        expense = super(HrExpense, self).message_new(msg_dict, dict(custom_values or {}, **vals))
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
        symbols, symbols_pattern, float_pattern = [], '', '[+-]?(\d+[.,]?\d*)'
        price = 0.0
        for currency in currencies:
            symbols.append(re.escape(currency.symbol))
            symbols.append(re.escape(currency.name))
        symbols_pattern = '|'.join(symbols)
        price_pattern = "((%s)?\s?%s\s?(%s)?)" % (symbols_pattern, float_pattern, symbols_pattern)
        matches = re.findall(price_pattern, expense_description)
        if matches:
            match = max(matches, key=lambda match: len([group for group in match if group])) # get the longuest match. e.g. "2 chairs 120$" -> the price is 120$, not 2
            full_str = match[0]
            currency_str = match[1] or match[3]
            price = match[2].replace(',', '.')

            if currency_str:
                currency = currencies.filtered(lambda c: currency_str in [c.symbol, c.name])[0]
                currency = currency or currencies[0]
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
        expense_template = self.env.ref(mail_template_id)
        rendered_body = expense_template._render({'expense': expense}, engine='ir.qweb')
        body = self.env['mail.render.mixin']._replace_local_links(rendered_body)
        # TDE TODO: seems louche, check to use notify
        if expense.employee_id.user_id.partner_id:
            expense.message_post(
                partner_ids=expense.employee_id.user_id.partner_id.ids,
                subject='Re: %s' % msg_dict.get('subject', ''),
                body=body,
                subtype_id=self.env.ref('mail.mt_note').id,
                email_layout_xmlid='mail.mail_notification_light',
            )
        else:
            self.env['mail.mail'].sudo().create({
                'email_from': self.env.user.email_formatted,
                'author_id': self.env.user.partner_id.id,
                'body_html': body,
                'subject': 'Re: %s' % msg_dict.get('subject', ''),
                'email_to': msg_dict.get('email_from', False),
                'auto_delete': True,
                'references': msg_dict.get('message_id'),
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
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Expense Report"
    _order = "accounting_date desc, id desc"
    _check_company_auto = True

    @api.model
    def _default_employee_id(self):
        return self.env.user.employee_id

    @api.model
    def _default_journal_id(self):
        """ The journal is determining the company of the accounting entries generated from expense. We need to force journal company and expense sheet company to be the same. """
        default_company_id = self.default_get(['company_id'])['company_id']
        journal = self.env['account.journal'].search([('type', '=', 'purchase'), ('company_id', '=', default_company_id)], limit=1)
        return journal.id

    @api.model
    def _default_bank_journal_id(self):
        default_company_id = self.default_get(['company_id'])['company_id']
        return self.env['account.journal'].search([('type', 'in', ['cash', 'bank']), ('company_id', '=', default_company_id)], limit=1)

    name = fields.Char('Expense Report Summary', required=True, tracking=True)
    expense_line_ids = fields.One2many('hr.expense', 'sheet_id', string='Expense Lines', copy=False)
    is_editable = fields.Boolean("Expense Lines Are Editable By Current User", compute='_compute_is_editable')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('approve', 'Approved'),
        ('post', 'Posted'),
        ('done', 'Done'),
        ('cancel', 'Refused')
    ], string='Status', index=True, readonly=True, tracking=True, copy=False, default='draft', required=True, help='Expense Report State')
    payment_state = fields.Selection(selection=PAYMENT_STATE_SELECTION, string="Payment Status",
        store=True, readonly=True, copy=False, tracking=True, compute='_compute_payment_state')
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, readonly=True, tracking=True, states={'draft': [('readonly', False)]}, default=_default_employee_id, check_company=True, domain= lambda self: self.env['hr.expense']._get_employee_id_domain())
    address_id = fields.Many2one('res.partner', compute='_compute_from_employee_id', store=True, readonly=False, copy=True, string="Employee Home Address", check_company=True)
    payment_mode = fields.Selection(related='expense_line_ids.payment_mode', readonly=True, string="Paid By", tracking=True)
    user_id = fields.Many2one('res.users', 'Manager', compute='_compute_from_employee_id', store=True, readonly=True, copy=False, states={'draft': [('readonly', False)]}, tracking=True, domain=lambda self: [('groups_id', 'in', self.env.ref('hr_expense.group_hr_expense_team_approver').id)])
    total_amount = fields.Monetary('Total Amount', currency_field='currency_id', compute='_compute_amount', store=True, tracking=True)
    amount_residual = fields.Monetary(
        string="Amount Due", store=True,
        currency_field='currency_id',
        related='account_move_id.amount_residual')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.company.currency_id)
    attachment_number = fields.Integer(compute='_compute_attachment_number', string='Number of Attachments')
    journal_id = fields.Many2one('account.journal', string='Expense Journal', states={'done': [('readonly', True)], 'post': [('readonly', True)]}, check_company=True, domain="[('type', '=', 'purchase'), ('company_id', '=', company_id)]",
        default=_default_journal_id, help="The journal used when the expense is done.")
    bank_journal_id = fields.Many2one('account.journal', string='Bank Journal', states={'done': [('readonly', True)], 'post': [('readonly', True)]}, check_company=True, domain="[('type', 'in', ['cash', 'bank']), ('company_id', '=', company_id)]",
        default=_default_bank_journal_id, help="The payment method used when the expense is paid by the company.")
    accounting_date = fields.Date("Accounting Date")
    account_move_id = fields.Many2one('account.move', string='Journal Entry', ondelete='restrict', copy=False, readonly=True)
    department_id = fields.Many2one('hr.department', compute='_compute_from_employee_id', store=True, readonly=False, copy=False, string='Department', states={'post': [('readonly', True)], 'done': [('readonly', True)]})
    is_multiple_currency = fields.Boolean("Handle lines with different currencies", compute='_compute_is_multiple_currency')
    can_reset = fields.Boolean('Can Reset', compute='_compute_can_reset')
    can_approve = fields.Boolean('Can Approve', compute='_compute_can_approve')
    approval_date = fields.Datetime('Approval Date', readonly=True)

    _sql_constraints = [
        ('journal_id_required_posted', "CHECK((state IN ('post', 'done') AND journal_id IS NOT NULL) OR (state NOT IN ('post', 'done')))", 'The journal must be set on posted expense'),
    ]

    @api.depends('expense_line_ids.total_amount_company')
    def _compute_amount(self):
        for sheet in self:
            sheet.total_amount = sum(sheet.expense_line_ids.mapped('total_amount_company'))

    @api.depends('account_move_id.payment_state')
    def _compute_payment_state(self):
        for sheet in self:
            sheet.payment_state = sheet.account_move_id.payment_state or 'not_paid'

    def _compute_attachment_number(self):
        for sheet in self:
            sheet.attachment_number = sum(sheet.expense_line_ids.mapped('attachment_number'))

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
        is_approver = self.user_has_groups('hr_expense.group_hr_expense_team_approver, hr_expense.group_hr_expense_user')
        is_manager = self.user_has_groups('hr_expense.group_hr_expense_manager')
        for sheet in self:
            sheet.can_approve = is_manager or (is_approver and sheet.employee_id.user_id != self.env.user)

    @api.depends('employee_id')
    def _compute_from_employee_id(self):
        for sheet in self:
            sheet.address_id = sheet.employee_id.sudo().address_home_id
            sheet.department_id = sheet.employee_id.department_id
            sheet.user_id = sheet.employee_id.expense_manager_id or sheet.employee_id.parent_id.user_id

    @api.depends_context('uid')
    @api.depends('employee_id', 'state')
    def _compute_is_editable(self):
        is_manager = self.user_has_groups('hr_expense.group_hr_expense_manager')
        is_approver = self.user_has_groups('hr_expense.group_hr_expense_user')
        for report in self:
            # Employee can edit his own expense in draft only
            is_editable = (report.employee_id.user_id == self.env.user and report.state == 'draft') or (is_manager and report.state in ['draft', 'submit', 'approve'])
            if not is_editable and report.state in ['draft', 'submit', 'approve']:
                # expense manager can edit, unless it's own expense
                current_managers = report.employee_id.expense_manager_id | report.employee_id.parent_id.user_id | report.employee_id.department_id.manager_id.user_id
                is_editable = (is_approver or self.env.user in current_managers) and report.employee_id.user_id != self.env.user
            report.is_editable = is_editable

    @api.constrains('expense_line_ids')
    def _check_payment_mode(self):
        for sheet in self:
            expense_lines = sheet.mapped('expense_line_ids')
            if expense_lines and any(expense.payment_mode != expense_lines[0].payment_mode for expense in expense_lines):
                raise ValidationError(_("Expenses must be paid by the same entity (Company or employee)."))

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

    @api.model
    def create(self, vals):
        context = clean_context(self.env.context)
        context.update({
            'mail_create_nosubscribe': True,
            'mail_auto_subscribe_no_notify': True
        })
        sheet = super(HrExpenseSheet, self.with_context(context)).create(vals)
        sheet.activity_update()
        return sheet

    @api.ondelete(at_uninstall=False)
    def _unlink_except_posted_or_paid(self):
        for expense in self:
            if expense.state in ['post', 'done']:
                raise UserError(_('You cannot delete a posted or paid expense.'))

    # --------------------------------------------
    # Mail Thread
    # --------------------------------------------

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'approve':
            return self.env.ref('hr_expense.mt_expense_approved')
        elif 'state' in init_values and self.state == 'cancel':
            return self.env.ref('hr_expense.mt_expense_refused')
        elif 'state' in init_values and self.state == 'done':
            return self.env.ref('hr_expense.mt_expense_paid')
        return super(HrExpenseSheet, self)._track_subtype(init_values)

    def _message_auto_subscribe_followers(self, updated_values, subtype_ids):
        res = super(HrExpenseSheet, self)._message_auto_subscribe_followers(updated_values, subtype_ids)
        if updated_values.get('employee_id'):
            employee = self.env['hr.employee'].browse(updated_values['employee_id'])
            if employee.user_id:
                res.append((employee.user_id.partner_id.id, subtype_ids, False))
        return res

    # --------------------------------------------
    # Actions
    # --------------------------------------------

    def action_sheet_move_create(self):
        samples = self.mapped('expense_line_ids.sample')
        if samples.count(True):
            if samples.count(False):
                raise UserError(_("You can't mix sample expenses and regular ones"))
            self.write({'state': 'post'})
            return

        if any(sheet.state != 'approve' for sheet in self):
            raise UserError(_("You can only generate accounting entry for approved expense(s)."))

        if any(not sheet.journal_id for sheet in self):
            raise UserError(_("Specify expense journal to generate accounting entries."))

        expense_line_ids = self.mapped('expense_line_ids')\
            .filtered(lambda r: not float_is_zero(r.total_amount, precision_rounding=(r.currency_id or self.env.company.currency_id).rounding))
        res = expense_line_ids.with_context(clean_context(self.env.context)).action_move_create()
        for sheet in self.filtered(lambda s: not s.accounting_date):
            sheet.accounting_date = sheet.account_move_id.date
        to_post = self.filtered(lambda sheet: sheet.payment_mode == 'own_account' and sheet.expense_line_ids)
        to_post.write({'state': 'post'})
        (self - to_post).write({'state': 'done'})
        self.activity_update()
        return res

    def action_unpost(self):
        self = self.with_context(clean_context(self.env.context))
        moves = self.account_move_id
        self.write({
            'account_move_id': False,
            'state': 'draft',
        })
        draft_moves = moves.filtered(lambda m: m.state == 'draft')
        draft_moves.unlink()
        (moves - draft_moves)._reverse_moves(cancel=True)

    def action_get_attachment_view(self):
        res = self.env['ir.actions.act_window']._for_xml_id('base.action_attachment')
        res['domain'] = [('res_model', '=', 'hr.expense'), ('res_id', 'in', self.expense_line_ids.ids)]
        res['context'] = {
            'default_res_model': 'hr.expense.sheet',
            'default_res_id': self.id,
            'create': False,
            'edit': False,
        }
        return res

    def action_open_account_move(self):
        self.ensure_one()
        return {
            'name': self.account_move_id.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.account_move_id.id
        }

    # --------------------------------------------
    # Business
    # --------------------------------------------

    def set_to_paid(self):
        self.write({'state': 'done'})

    def action_submit_sheet(self):
        self.write({'state': 'submit'})
        self.activity_update()

    def _check_can_approve(self):
        if not self.user_has_groups('hr_expense.group_hr_expense_team_approver'):
            raise UserError(_("Only Managers and HR Officers can approve expenses"))
        elif not self.user_has_groups('hr_expense.group_hr_expense_manager'):
            current_managers = self.employee_id.expense_manager_id | self.employee_id.parent_id.user_id | self.employee_id.department_id.manager_id.user_id

            if self.employee_id.user_id == self.env.user:
                raise UserError(_("You cannot approve your own expenses"))

            if not self.env.user in current_managers and not self.user_has_groups('hr_expense.group_hr_expense_user') and self.employee_id.expense_manager_id != self.env.user:
                raise UserError(_("You can only approve your department expenses"))

    def approve_expense_sheets(self):
        self._check_can_approve()

        duplicates = self.expense_line_ids.duplicate_expense_ids.filtered(lambda exp: exp.state in ['approved', 'done'])
        if duplicates:
            action = self.env["ir.actions.act_window"]._for_xml_id('hr_expense.hr_expense_approve_duplicate_action')
            action['context'] = {'default_sheet_ids': self.ids, 'default_expense_ids': duplicates.ids}
            return action
        self._do_approve()

    def _do_approve(self):
        self._check_can_approve()

        notification = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('There are no expense reports to approve.'),
                'type': 'warning',
                'sticky': False,  #True/False will display for few seconds if false
            },
        }

        filtered_sheet = self.filtered(lambda s: s.state in ['submit', 'draft'])
        if not filtered_sheet:
            return notification
        for sheet in filtered_sheet:
            sheet.write({'state': 'approve', 'user_id': sheet.user_id.id or self.env.user.id})
        notification['params'].update({
            'title': _('The expense reports were successfully approved.'),
            'type': 'success',
            'next': {'type': 'ir.actions.act_window_close'},
        })

        self.activity_update()
        return notification

    def paid_expense_sheets(self):
        self.write({'state': 'done'})

    def refuse_sheet(self, reason):
        if not self.user_has_groups('hr_expense.group_hr_expense_team_approver'):
            raise UserError(_("Only Managers and HR Officers can approve expenses"))
        elif not self.user_has_groups('hr_expense.group_hr_expense_manager'):
            current_managers = self.employee_id.expense_manager_id | self.employee_id.parent_id.user_id | self.employee_id.department_id.manager_id.user_id

            if self.employee_id.user_id == self.env.user:
                raise UserError(_("You cannot refuse your own expenses"))

            if not self.env.user in current_managers and not self.user_has_groups('hr_expense.group_hr_expense_user') and self.employee_id.expense_manager_id != self.env.user:
                raise UserError(_("You can only refuse your department expenses"))

        self.write({'state': 'cancel'})
        for sheet in self:
            sheet.message_post_with_view('hr_expense.hr_expense_template_refuse_reason', values={'reason': reason, 'is_sheet': True, 'name': sheet.name})
        self.activity_update()

    def reset_expense_sheets(self):
        if not self.can_reset:
            raise UserError(_("Only HR Officers or the concerned employee can reset to draft."))
        self.mapped('expense_line_ids').write({'is_refused': False})
        self.write({'state': 'draft', 'approval_date': False})
        self.activity_update()
        return True

    def _get_responsible_for_approval(self):
        if self.user_id:
            return self.user_id
        elif self.employee_id.parent_id.user_id:
            return self.employee_id.parent_id.user_id
        elif self.employee_id.department_id.manager_id.user_id:
            return self.employee_id.department_id.manager_id.user_id
        return self.env['res.users']

    def activity_update(self):
        for expense_report in self.filtered(lambda hol: hol.state == 'submit'):
            self.activity_schedule(
                'hr_expense.mail_act_expense_approval',
                user_id=expense_report.sudo()._get_responsible_for_approval().id or self.env.user.id)
        self.filtered(lambda hol: hol.state == 'approve').activity_feedback(['hr_expense.mail_act_expense_approval'])
        self.filtered(lambda hol: hol.state in ('draft', 'cancel')).activity_unlink(['hr_expense.mail_act_expense_approval'])

    def action_register_payment(self):
        ''' Open the account.payment.register wizard to pay the selected journal entries.
        :return: An action opening the account.payment.register wizard.
        '''
        return {
            'name': _('Register Payment'),
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.account_move_id.ids,
                'default_partner_bank_id': self.employee_id.sudo().bank_account_id.id,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }
