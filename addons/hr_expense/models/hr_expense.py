# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import email_split
import openerp.addons.decimal_precision as dp


class HrExpense(models.Model):

    _name = "hr.expense"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Expense"
    _order = "date desc, id desc"

    name = fields.Char(string='Expense Description', readonly=True, required=True, states={'draft': [('readonly', False)]})
    date = fields.Date(readonly=True, states={'draft': [('readonly', False)]}, default=fields.Date.context_today, string="Date")
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1))
    product_id = fields.Many2one('product.product', string='Product', readonly=True, states={'draft': [('readonly', False)]}, domain=[('can_be_expensed', '=', True)], required=True)
    product_uom_id = fields.Many2one('product.uom', string='Unit of Measure', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env['product.uom'].search([], limit=1, order='id'))
    unit_amount = fields.Float(string='Unit Price', readonly=True, required=True, states={'draft': [('readonly', False)]}, digits=dp.get_precision('Product Price'))
    quantity = fields.Float(required=True, readonly=True, states={'draft': [('readonly', False)]}, digits=dp.get_precision('Product Unit of Measure'), default=1)
    tax_ids = fields.Many2many('account.tax', 'expense_tax', 'expense_id', 'tax_id', string='Taxes', states={'done': [('readonly', True)], 'post': [('readonly', True)]})
    untaxed_amount = fields.Float(string='Subtotal', store=True, compute='_compute_amount', digits=dp.get_precision('Account'))
    total_amount = fields.Float(string='Total', store=True, compute='_compute_amount', digits=dp.get_precision('Account'))
    company_id = fields.Many2one('res.company', string='Company', readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.user.company_id.currency_id)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', states={'post': [('readonly', True)], 'done': [('readonly', True)]}, oldname='analytic_account')
    account_id = fields.Many2one('account.account', string='Account', states={'post': [('readonly', True)], 'done': [('readonly', True)]}, default=lambda self: self.env['ir.property'].get('property_account_expense_categ_id', 'product.category'))
    description = fields.Text()
    payment_mode = fields.Selection([("own_account", "Employee (to reimburse)"), ("company_account", "Company")], default='own_account', states={'done': [('readonly', True)], 'post': [('readonly', True)]}, string="Payment By")
    attachment_number = fields.Integer(compute='_compute_attachment_number', string='Number of Attachments')
    state = fields.Selection([('draft', 'To Report'),
                              ('reported', 'Reported'),
                              ('done', 'Posted'),
                              ('refused', 'Refused')
        ], compute='_compute_state', default="draft", string='Status', index=True, readonly=True, copy=False, required=True, store=True,
        help="Status of the expense.")
    sheet_id = fields.Many2one('hr.expense.sheet', string="Expense Report", readonly=True)
    reference = fields.Char(string="Bill Reference")

    @api.depends('sheet_id', 'sheet_id.account_move_id', 'sheet_id.state')
    def _compute_state(self):
        for expense in self:
            if not expense.sheet_id:
                expense.state = "draft"
            elif expense.sheet_id.state == "cancel":
                expense.state = "refused"
            elif not expense.sheet_id.account_move_id:
                expense.state = "reported"
            else:
                expense.state = "done"

    @api.depends('quantity', 'unit_amount', 'tax_ids', 'currency_id')
    def _compute_amount(self):
        for expense in self:
            expense.untaxed_amount = expense.unit_amount * expense.quantity
            taxes = expense.tax_ids.compute_all(expense.unit_amount, expense.currency_id, expense.quantity, expense.product_id, expense.employee_id.user_id.partner_id)
            expense.total_amount = taxes.get('total_included')

    @api.multi
    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].read_group([('res_model', '=', 'hr.expense'), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for expense in self:
            expense.attachment_number = attachment.get(expense.id, 0)

    @api.multi
    def action_get_attachment_view(self):
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'hr.expense'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'hr.expense', 'default_res_id': self.id}
        return res

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            if not self.name:
                self.name = self.product_id.display_name or ''
            self.unit_amount = self.env['product.template']._price_get(self.product_id, 'standard_price')[self.product_id.id]
            self.product_uom_id = self.product_id.uom_id
            self.tax_ids = self.product_id.supplier_taxes_id
            account = self.product_id.product_tmpl_id._get_product_accounts()['expense']
            if account:
                self.account_id = account

    @api.onchange('product_uom_id')
    def _onchange_product_uom_id(self):
        if self.product_id and self.product_uom_id.category_id != self.product_id.uom_id.category_id:
            raise UserError(_('Selected Unit of Measure does not belong to the same category as the product Unit of Measure'))

    @api.multi
    def view_sheet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.expense.sheet',
            'target': 'current',
            'res_id': self.sheet_id.id
        }

    @api.multi
    def submit_expenses(self):
        if any(expense.state != 'draft' for expense in self):
            raise UserError(_("You cannot report twice the same line!"))
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.expense.sheet',
            'target': 'current',
            'context': {
                'default_expense_line_ids': [line.id for line in self],
                'default_employee_id': self[0].employee_id.id,
                'default_name': self[0].name if len(self.ids) == 1 else ''
            }
        }

    def _prepare_move_line(self, line):
        '''
        This function prepares move line of account.move related to an expense
        '''
        partner_id = self.employee_id.address_home_id.commercial_partner_id.id
        return {
            'date_maturity': line.get('date_maturity'),
            'partner_id': partner_id,
            'name': line['name'][:64],
            'date': self.sheet_id.accounting_date,
            'debit': line['price'] > 0 and line['price'],
            'credit': line['price'] < 0 and - line['price'],
            'account_id': line['account_id'],
            'analytic_line_ids': line.get('analytic_line_ids'),
            'amount_currency': line['price'] > 0 and abs(line.get('amount_currency')) or - abs(line.get('amount_currency')),
            'currency_id': line.get('currency_id'),
            'tax_line_id': line.get('tax_line_id'),
            'ref': line.get('ref'),
            'quantity': line.get('quantity', 1.00),
            'product_id': line.get('product_id'),
            'product_uom_id': line.get('uom_id'),
            'analytic_account_id': line.get('analytic_account_id'),
        }

    @api.multi
    def _compute_expense_totals(self, company_currency, account_move_lines, move_date):
        '''
        internal method used for computation of total amount of an expense in the company currency and
        in the expense currency, given the account_move_lines that will be created. It also do some small
        transformations at these account_move_lines (for multi-currency purposes)

        :param account_move_lines: list of dict
        :rtype: tuple of 3 elements (a, b ,c)
            a: total in company currency
            b: total in hr.expense currency
            c: account_move_lines potentially modified
        '''
        self.ensure_one()
        total = 0.0
        total_currency = 0.0
        for line in account_move_lines:
            line['currency_id'] = False
            line['amount_currency'] = False
            if self.currency_id != company_currency:
                line['currency_id'] = self.currency_id.id
                line['amount_currency'] = line['price']
                line['price'] = self.currency_id.with_context(date=move_date or fields.Date.context_today(self)).compute(line['price'], company_currency)
            total -= line['price']
            total_currency -= line['amount_currency'] or line['price']
        return total, total_currency, account_move_lines

    @api.multi
    def action_move_create(self):
        '''
        main function that is called when trying to create the accounting entries related to an expense
        '''
        journal_dict = {}
        for expense in self:
            acc_date = expense.sheet_id.accounting_date or fields.Date.context_today(self)
            jrn = expense.sheet_id.bank_journal_id if expense.payment_mode == 'company_account' else expense.sheet_id.journal_id
            journal_dict.setdefault(jrn, [])
            journal_dict[jrn].append(expense)

        for journal, expense_list in journal_dict.items():
            #create the move that will contain the accounting entries
            move = self.env['account.move'].create({
                'journal_id': journal.id,
                'company_id': self.env.user.company_id.id,
                'date': acc_date,
            })
            for expense in expense_list:
                company_currency = expense.company_id.currency_id
                diff_currency_p = expense.currency_id != company_currency
                #one account.move.line per expense (+taxes..)
                move_lines = expense._move_line_get()

                #create one more move line, a counterline for the total on payable account
                total, total_currency, move_lines = expense._compute_expense_totals(company_currency, move_lines, acc_date)
                if expense.payment_mode == 'company_account':
                    if not expense.sheet_id.bank_journal_id.default_credit_account_id:
                        raise UserError(_("No credit account found for the %s journal, please configure one.") % (expense.sheet_id.bank_journal_id.name))
                    emp_account = expense.sheet_id.bank_journal_id.default_credit_account_id.id
                else:
                    if not expense.employee_id.address_home_id:
                        raise UserError(_("No Home Address found for the employee %s, please configure one.") % (expense.employee_id.name))
                    emp_account = expense.employee_id.address_home_id.property_account_payable_id.id

                move_lines.append({
                        'type': 'dest',
                        'name': expense.employee_id.name,
                        'price': total,
                        'account_id': emp_account,
                        'date_maturity': acc_date,
                        'amount_currency': diff_currency_p and total_currency or False,
                        'currency_id': diff_currency_p and expense.currency_id.id or False,
                        'ref': expense.employee_id.address_home_id.ref or False
                        })

                #convert eml into an osv-valid format
                lines = map(lambda x: (0, 0, expense._prepare_move_line(x)), move_lines)
                move.write({'line_ids': lines})
                expense.sheet_id.write({'account_move_id': move.id})
                if expense.payment_mode == 'company_account':
                    expense.sheet_id.paid_expense_sheets()
            move.post()
        return True

    @api.multi
    def _move_line_get(self):
        account_move = []
        for expense in self:
            if expense.account_id:
                account = expense.account_id
            elif expense.product_id:
                account = expense.product_id.product_tmpl_id._get_product_accounts()['expense']
                if not account:
                    raise UserError(_("No Expense account found for the product %s (or for it's category), please configure one.") % (expense.product_id.name))
            else:
                account = self.env['ir.property'].with_context(force_company=expense.company_id.id).get('property_account_expense_categ_id', 'product.category')
                if not account:
                    raise UserError(_('Please configure Default Expense account for Product expense: `property_account_expense_categ_id`.'))

            move_line = {
                    'type': 'src',
                    'name': expense.name.split('\n')[0][:64],
                    'price_unit': expense.unit_amount,
                    'quantity': expense.quantity,
                    'price': expense.total_amount,
                    'account_id': account.id,
                    'product_id': expense.product_id.id,
                    'uom_id': expense.product_uom_id.id,
                    'analytic_account_id': expense.analytic_account_id.id,
            }
            account_move.append(move_line)

            # Calculate tax lines and adjust base line
            taxes = expense.tax_ids.compute_all(expense.unit_amount, expense.currency_id, expense.quantity, expense.product_id)
            account_move[-1]['price'] = taxes['total_excluded']
            account_move[-1]['tax_ids'] = expense.tax_ids.id
            for tax in taxes['taxes']:
                account_move.append({
                    'type': 'tax',
                    'name': tax['name'],
                    'price_unit': tax['amount'],
                    'quantity': 1,
                    'price': tax['amount'],
                    'account_id': tax['account_id'] or move_line['account_id'],
                    'tax_line_id': tax['id'],
                })
        return account_move

    @api.multi
    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'hr.expense'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'hr.expense', 'default_res_id': self.id}
        return res

    @api.model
    def get_empty_list_help(self, help_message):
        if help_message:
            alias_record = self.env.ref('hr_expense.mail_alias_expense')
            if alias_record and alias_record.alias_domain and alias_record.alias_name:
                dynamic_help = '<p>%s</p>' % _("""Create a new expense, or send receipts by email to %(link)s to automatically create new expenses.""") % {
                    'link': "<a href='mailto:%(email)s'>%(email)s</a>" % {'email': '%s@%s' % (alias_record.alias_name, alias_record.alias_domain)}
                }
                return '<p class="oe_view_nocontent_create">%s</p>%s%s' % (
                    _('Click to add a new expense'),
                    dynamic_help,
                    help_message)
        return super(HrExpense, self).get_empty_list_help(help_message)

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        if custom_values is None:
            custom_values = {}

        # Retrieve the email address from the email field. The string is constructed like
        # 'foo <bar>'. We will extract 'bar' from this
        email_address = email_split(msg_dict.get('email_from', False))[0]

        # Look after an employee who has this email address or an employee for whom the related
        # user has this email address. In the case not employee is found, we send back an email
        # to explain that the expense will not be created.
        employee = self.env['hr.employee'].search([('work_email', 'ilike', email_address)], limit=1)
        if not employee:
            employee = self.env['hr.employee'].search([('user_id.email', 'ilike', email_address)], limit=1)
        if not employee:
            # Send back an email to explain why the expense has not been created
            mail_template = self.env.ref('hr_expense.mail_template_data_expense_unknown_email_address')
            mail_template.with_context(email_to=email_address).send_mail(self.env.ref('base.module_hr_expense').id)
            return False

        expense_description = msg_dict.get('subject', '')

        # Match the first occurence of '[]' in the string and extract the content inside it
        # Example: '[foo] bar (baz)' becomes 'foo'. This is potentially the product code
        # of the product to encode on the expense. If not, take the default product instead
        # which is 'Fixed Cost'
        default_product = self.env.ref('hr_expense.product_product_fixed_cost')
        pattern = '\[([^)]*)\]'
        product_code = re.search(pattern, expense_description)
        if product_code is None:
            product = default_product
        else:
            expense_description = expense_description.replace(product_code.group(), '')
            product = self.env['product.product'].search([('default_code', 'ilike', product_code.group(1))]) or default_product

        pattern = '[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?'
        # Match the last occurence of a float in the string
        # Example: '[foo] 50.3 bar 34.5' becomes '34.5'. This is potentially the price
        # to encode on the expense. If not, take 1.0 instead
        expense_price = re.findall(pattern, expense_description)
        # TODO: International formatting
        if not expense_price:
            price = 1.0
        else:
            price = expense_price[-1][0]
            expense_description = expense_description.replace(price, '')
            try:
                price = float(price)
            except ValueError:
                price = 1.0

        custom_values.update({
            'name': expense_description.strip(),
            'employee_id': employee.id,
            'product_id': product.id,
            'product_uom_id': product.uom_id.id,
            'quantity': 1,
            'unit_amount': price
        })
        return super(HrExpense, self).message_new(msg_dict, custom_values)

class HrExpenseSheet(models.Model):

    _name = "hr.expense.sheet"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Expense Report"
    _order = "accounting_date desc"

    name = fields.Char(string='Expense Report Summary', required=True)
    expense_line_ids = fields.One2many('hr.expense', 'sheet_id', string='Expense Lines', states={'done': [('readonly', True)], 'post': [('readonly', True)]}, copy=False)
    state = fields.Selection([('submit', 'Submitted'),
                              ('approve', 'Approved'),
                              ('post', 'Posted'),
                              ('done', 'Paid'),
                              ('cancel', 'Refused')
                              ], string='Status', index=True, readonly=True, track_visibility='onchange', copy=False, default='submit', required=True,
        help='Expense Report State')
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, readonly=True, states={'submit': [('readonly', False)]}, default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1))
    address_id = fields.Many2one('res.partner', string="Employee Home Address")
    payment_mode = fields.Selection([("own_account", "Employee (to reimburse)"), ("company_account", "Company")], related='expense_line_ids.payment_mode', default='own_account', readonly=True, string="Payment By")
    responsible_id = fields.Many2one('res.users', 'Validation By', readonly=True, copy=False, states={'submit': [('readonly', False)], 'submit': [('readonly', False)]})
    total_amount = fields.Float(string='Total Amount', store=True, compute='_compute_amount', digits=dp.get_precision('Account'))
    company_id = fields.Many2one('res.company', string='Company', readonly=True, states={'submit': [('readonly', False)]}, default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, states={'submit': [('readonly', False)]}, default=lambda self: self.env.user.company_id.currency_id)
    attachment_number = fields.Integer(compute='_compute_attachment_number', string='Number of Attachments')
    journal_id = fields.Many2one('account.journal', string='Expense Journal', states={'done': [('readonly', True)], 'post': [('readonly', True)]},
        default=lambda self: self.env['ir.model.data'].xmlid_to_object('hr_expense.hr_expense_account_journal') or self.env['account.journal'].search([('type', '=', 'purchase')], limit=1),
        help="The journal used when the expense is done.")
    bank_journal_id = fields.Many2one('account.journal', string='Bank Journal', states={'done': [('readonly', True)], 'post': [('readonly', True)]}, default=lambda self: self.env['account.journal'].search([('type', 'in', ['case', 'bank'])], limit=1), help="The payment method used when the expense is paid by the company.")
    accounting_date = fields.Date(string="Accounting Date")
    account_move_id = fields.Many2one('account.move', string='Journal Entry', copy=False, track_visibility="onchange")
    department_id = fields.Many2one('hr.department', string='Department', states={'post': [('readonly', True)], 'done': [('readonly', True)]})

    @api.multi
    def check_consistency(self):
        if any(sheet.employee_id != self[0].employee_id for sheet in self):
            raise UserError(_("Expenses must belong to the same Employee."))

        expense_lines = self.mapped('expense_line_ids')
        if expense_lines and any(expense.payment_mode != expense_lines[0].payment_mode for expense in expense_lines):
            raise UserError(_("Expenses must have been paid by the same entity (Company or employee)"))

    @api.model
    def create(self, vals):
        sheet = super(HrExpenseSheet, self).create(vals)
        self.check_consistency()
        if vals.get('employee_id'):
            sheet._add_followers()
        return sheet

    @api.multi
    def write(self, vals):
        res = super(HrExpenseSheet, self).write(vals)
        self.check_consistency()
        if vals.get('employee_id'):
            self._add_followers()
        return res

    @api.multi
    def set_to_paid(self):
        self.write({'state': 'done'})

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'approve':
            return 'hr_expense.mt_expense_approved'
        elif 'state' in init_values and self.state == 'submit':
            return 'hr_expense.mt_expense_confirmed'
        elif 'state' in init_values and self.state == 'cancel':
            return 'hr_expense.mt_expense_refused'
        return super(HrExpenseSheet, self)._track_subtype(init_values)

    def _add_followers(self):
        user_ids = []
        employee = self.employee_id
        if employee.user_id:
            user_ids.append(employee.user_id.id)
        if employee.parent_id:
            user_ids.append(employee.parent_id.user_id.id)
        if employee.department_id and employee.department_id.manager_id and employee.parent_id != employee.department_id.manager_id:
            user_ids.append(employee.department_id.manager_id.user_id.id)
        self.message_subscribe_users(user_ids=user_ids)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        self.address_id = self.employee_id.address_home_id
        self.department_id = self.employee_id.department_id

    @api.one
    @api.depends('expense_line_ids')
    def _compute_amount(self):
        self.total_amount = sum(self.expense_line_ids.mapped('total_amount'))

    # FIXME: A 4 command is missing to explicitly declare the one2many relation
    # between the sheet and the lines when using 'default_expense_line_ids':[ids]
    # in the context. A fix from chm-odoo should come since
    # several saas versions but sadly I had to add this hack to avoid this
    # issue
    @api.model
    def _add_missing_default_values(self, values):
        values = super(HrExpenseSheet, self)._add_missing_default_values(values)
        if self.env.context.get('default_expense_line_ids', False):
            lines_to_add = []
            for line in values.get('expense_line_ids', []):
                if line[0] == 1:
                    lines_to_add.append([4, line[1], False])
            values['expense_line_ids'] = lines_to_add + values['expense_line_ids']
        return values

    @api.one
    def _compute_attachment_number(self):
        self.attachment_number = sum(self.expense_line_ids.mapped('attachment_number'))

    @api.multi
    def refuse_expenses(self, reason):
        self.write({'state': 'cancel'})
        for sheet in self:
            body = (_("Your Expense %s has been refused.<br/><ul class=o_timeline_tracking_value_list><li>Reason<span> : </span><span class=o_timeline_tracking_value>%s</span></li></ul>") % (sheet.name, reason))
            sheet.message_post(body=body)

    @api.multi
    def approve_expense_sheets(self):
        self.message_post(body=_("The expense has been validated by %s") % (self.env.user.name))
        self.write({'state': 'approve', 'responsible_id': self.env.user.id})

    @api.multi
    def refuse_expense_sheets(self, reason):
        self.write({'state': 'cancel'})
        for sheet in self:
            body = (_("Your Expense %s has been refused.<br/><ul class=o_timeline_tracking_value_list><li>Reason<span> : </span><span class=o_timeline_tracking_value>%s</span></li></ul>") % (sheet.name, reason))
            sheet.message_post(body=body)

    @api.multi
    def paid_expense_sheets(self):
        self.write({'state': 'done'})

    @api.multi
    def reset_expense_sheets(self):
        return self.write({'state': 'submit'})

    @api.multi
    def action_sheet_move_create(self):
        if any(sheet.state != 'approve' for sheet in self):
            raise UserError(_("You can only generate accounting entry for approved expense(s)."))

        if any(not sheet.journal_id for sheet in self):
            raise UserError(_("Expenses must have an expense journal specified to generate accounting entries."))

        res = self.mapped('expense_line_ids').action_move_create()

        if not self.accounting_date:
            self.accounting_date = self.account_move_id.date

        if self.payment_mode=='own_account':
            self.write({'state': 'post'})
        else:
            self.write({'state': 'done'})
        return res

    @api.multi
    def action_get_attachment_view(self):
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'hr.expense'), ('res_id', 'in', self.expense_line_ids.ids)]
        res['context'] = {'default_res_model': 'hr.expense.sheet', 'default_res_id': self.id}
        return res
