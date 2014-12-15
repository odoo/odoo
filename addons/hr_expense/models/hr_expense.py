# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.exceptions import UserError

import openerp.addons.decimal_precision as dp


class HrExpenseSheet(models.Model):
    _name = "hr.expense.sheet"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Expense Sheet"
    _order = "id desc"

    name = fields.Char(readonly=True)
    date = fields.Date(readonly=True, default=fields.Date.context_today)
    journal_id = fields.Many2one('account.journal', string='Force Journal', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, help = "The journal used when the expense is done.")
    employee_payable_account_id = fields.Many2one('account.account', string='Employee Account', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, help="Employee payable account")
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, readonly=True)
    date_confirm = fields.Date(string='Confirmation Date', copy=False, readonly=True,
                                help="Date of the confirmation of the sheet expense. It's filled when the button Confirm is pressed.")
    date_valid = fields.Date(string='Validation Date', copy=False, readonly=True,
                              help="Date of the acceptation of the sheet expense. It's filled when the button Accept is pressed.")
    user_valid = fields.Many2one('res.users', string='Validation By', readonly=True, copy=False,
                                  states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    account_move_id = fields.Many2one('account.move', string='Ledger Posting', copy=False, readonly=True)
    line_ids = fields.One2many('hr.expense', 'expense_id', string='Expense Lines', copy=True)
    note = fields.Text()
    amount_untaxed = fields.Float(compute='_amount', string='Untaxed Amount', digits=dp.get_precision('Account'), store=True)
    amount_tax = fields.Float(compute='_amount', string='Taxes', digits=dp.get_precision('Account'), store=True)
    amount = fields.Float(compute='_amount', string='Total', digits=dp.get_precision('Account'), store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, default=lambda self: self.env.user.company_id.currency_id.id)
    department_id = fields.Many2one('hr.department', string='Department', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, default=lambda self: self.env['res.company']._company_default_get('hr.employee'))
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('cancel', 'Refused'),
        ('confirm', 'Submitted'),
        ('accepted', 'Approved'),
        ('done', 'Posted'),
        ('paid', 'Paid'),
        ],
        string='Status', readonly=True, track_visibility='onchange', copy=False, default='draft', required=True,
        help='When the expense request is created the status is \'Draft\'.\n It is confirmed by the user and request is sent to admin, the status is \'Waiting Confirmation\'.\
        \nIf the admin accepts it, the status is \'Accepted\'.\n If the accounting entries are made for the expense request, the status is \'Waiting Payment\'.')
    attachment_ids = fields.One2many('ir.attachment', 'res_id', compute="_get_attachment", string='Attachments')


    @api.multi
    def _get_attachment(self):
        self.attachment_ids = self.env['ir.attachment'].search(['|',
            '&', ('res_model', '=', 'hr.expense.sheet'), ('res_id', 'in', self.ids),
            '&', ('res_model', '=', 'hr.expense'), ('res_id', 'in', self.mapped("line_ids").ids)])

    @api.depends('line_ids.unit_amount', 'line_ids.unit_quantity', 'line_ids.state', 'line_ids.expense_tax_id')
    def _amount(self):
        for sheet in self:
            total = 0.0
            amount_untaxed = 0.0
            for line in sheet.line_ids.filtered(lambda expense: expense.state in ['accepted', 'done', 'paid']):
                total += line.amount
                amount_untaxed += line.amount_untaxed
            sheet.amount = total
            sheet.amount_untaxed = amount_untaxed
            sheet.amount_tax = total - amount_untaxed

    @api.onchange('currency_id')
    def onchange_currency_id(self):
        account_journal = self.env['account.journal'].search([('type', '=', 'purchase'), ('currency', '=', self.currency_id.id), ('company_id', '=', self.company_id.id)], limit=1)
        self.journal_id = account_journal.id

    @api.model
    def create(self, vals):
        employee_id = vals.get('employee_id', False)
        sheet = super(HrExpenseSheet, self).create(vals)
        if employee_id:
            sheet._add_follower(employee_id)
        return sheet

    @api.multi
    def write(self, vals):
        employee_id = vals.get('employee_id', False)
        res = super(HrExpenseSheet, self).write(vals)
        if employee_id:
            self._add_follower(employee_id)
        return res

    @api.multi
    def unlink(self):
        for sheet in self:
            if sheet.state not in ['draft', 'cancel']:
                raise UserError(_('You can only delete draft or cancelled expenses!'))
        return super(HrExpenseSheet, self).unlink()

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'accepted':
            return 'hr_expense.mt_expense_approved'
        elif 'state' in init_values and self.state == 'confirm':
            return 'hr_expense.mt_expense_confirmed'
        elif 'state' in init_values and self.state == 'cancel':
            return 'hr_expense.mt_expense_refused'
        return super(HrExpenseSheet, self)._track_subtype(init_values)


    def _add_follower(self, employee_id):
        employee = self.env['hr.employee'].browse(employee_id)
        if employee and employee.user_id:
            self.message_subscribe_users(user_ids=[employee.user_id.id])

    @api.multi
    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('id', 'in', self.attachment_ids.ids)]
        res['context'] = {'default_res_model': 'hr.expense.sheet', 'default_res_id': self.id}
        return res

    @api.multi
    def sheet_draft(self):
        for sheet in self:
            sheet.line_ids.write({'state': 'draft', 'expense_id': False})
        return self.write({'state': 'draft'})

    @api.multi
    def sheet_confirm(self):
        for sheet in self:
            if not sheet.line_ids:
                raise UserError(_('You cannot submit expense which has no expense line.'))
            if sheet.employee_id and sheet.employee_id.parent_id.user_id:
                self.message_subscribe_users(user_ids = sheet.employee_id.parent_id.user_id.ids)
        return self.write({'state': 'confirm', 'date_confirm': fields.Date.context_today(self)})

    @api.multi
    def sheet_accept(self):
        for sheet in self:
            sheet.line_ids.filtered(lambda expense: expense.state != 'cancel').approve_expenses()
        return self.write({'state': 'accepted', 'date_valid': fields.Date.context_today(self), 'user_valid': self._uid})

    @api.multi
    def sheet_cancelled(self):
        for sheet in self:
            sheet.line_ids.cancel_expenses()
        return self.write({'state': 'cancel'})

    @api.multi
    def _prepare_account_move(self):
        '''
        This method prepare the creation of the account move related to the given expense.
        :return: mapping between fieldname and value of account move to create
        '''
        if self.journal_id:
            journal_id = self.journal_id.id
        else:
            journal_id = self.env['account.journal'].search([('type', '=', 'purchase'), ('company_id', '=', self.company_id.id)], limit=1)
            if not journal_id:
                raise UserError(_("No expense journal found. Please make sure you have a journal with type 'purchase' configured."))
            journal_id = journal_id.id

        move_dict = self.env['account.move'].account_move_prepare(journal_id, date=self.date_confirm, ref=self.name, company_id=self.company_id.id)

        move_lines = self.line_ids._prepare_account_move_entry()

        company_currency = self.company_id.currency_id

        total, total_currency, account_move_line = self._compute_account_move_totals(company_currency, move_lines)

        account_id = self.employee_payable_account_id.id or False
        move_lines.append({
            'price': total,
            'account_id': account_id,
            'name': move_dict['ref'],
        })

        move_lines = map(lambda sheet: (0, 0, self._convert_move_line(sheet, self.employee_id.address_home_id, self.date_confirm)), account_move_line)
        move_dict['line_id'] = move_lines
        return move_dict

    def _convert_move_line(self, move_line, partner, date):
        partner_id = self.env['res.partner']._find_accounting_partner(partner).id
        return {
            'date_maturity': move_line.get('date_maturity', False),
            'partner_id': partner_id,
            'name': move_line['name'],
            'date': date,
            'debit': move_line['price'] > 0 and move_line['price'],
            'credit': move_line['price'] < 0 and -move_line['price'],
            'account_id': move_line['account_id'],
            'analytic_lines': move_line.get('analytic_lines', False),
            'amount_currency': move_line['price'] > 0 and abs(move_line.get('amount_currency', False)) or -abs(move_line.get('amount_currency', False)),
            'currency_id': move_line.get('currency_id', False),
            'tax_code_id': move_line.get('tax_code_id', False),
            'tax_amount': move_line.get('tax_amount', False),
            'ref': move_line.get('ref', False),
            'quantity': move_line.get('quantity', 1.00),
            'product_id': move_line.get('product_id', False),
            'product_uom_id': move_line.get('uos_id', False),
            'analytic_account_id': move_line.get('account_analytic_id', False),
        }

    @api.multi
    def _compute_account_move_totals(self, company_currency, account_move_lines):
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
        total = 0.0
        total_currency = 0.0
        for line in account_move_lines:
            if self.currency_id != company_currency:
                line['currency_id'] = self.currency_id.id
                line['amount_currency'] = line['price']
                line['price'] = self.currency_id.with_context(date = self.date_confirm or fields.Date.context_today(self)).compute(line['price'], company_currency)
            else:
                line['amount_currency'] = False
                line['currency_id'] = False
            total -= line['price']
            total_currency -= line['amount_currency'] or line['price']
        return total, total_currency, account_move_lines

    @api.multi
    def action_move_create(self):
        '''
        main function that is called when trying to create the accounting entries related to an expense
        '''
        AccountMove = self.env['account.move']
        for sheet in self:
            if not sheet.employee_payable_account_id:
                raise UserError(_('No employee account payable found for the expense '))

            #create the move that will contain the accounting entries
            move = AccountMove.create(sheet._prepare_account_move())
            journal_id = move.journal_id
            # post the journal entry if 'Skip 'Draft' State for Manual Entries' is checked
            if journal_id.entry_posted:
                move.button_validate()
            sheet.write({'account_move_id': move.id, 'state': 'done'})
            sheet.line_ids.filtered(lambda expense: expense.state == 'accepted').done_expenses()
        return True

    @api.multi
    def action_view_move(self):
        '''
        This function returns an action that display existing account.move of given expense ids.
        '''
        self.ensure_one()
        try:
            view_id = self.env.ref('account.view_move_form').id
        except ValueError, e:
            view_id = False
        result = {
            'name': _('Expense Account Move'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': self.account_move_id.id,
        }
        return result

class HrExpense(models.Model):
    _name = "hr.expense"
    _description = "Employee Expense"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = "sequence, date"


    name = fields.Char(string='Description', required=True, readonly=True, states={'draft': [('readonly', False)]})
    date = fields.Date(required=True, readonly=True, states={'draft': [('readonly', False)]}, default=fields.Date.context_today)
    expense_id = fields.Many2one('hr.expense.sheet', string='Expense', readonly=True, ondelete='cascade')
    amount = fields.Float(string='Total', store=True, compute='_amount', digits=dp.get_precision('Account'))
    amount_untaxed = fields.Float(string='Subtotal', store=True, compute='_amount', digits=dp.get_precision('Account'))
    unit_amount = fields.Float(string='Unit Price', readonly=True, states={'draft': [('readonly', False)]}, digits=dp.get_precision('Product Price'))
    unit_quantity = fields.Float(string='Quantity', required=True, readonly=True, states={'draft': [('readonly', False)]}, digits= dp.get_precision('Product Unit of Measure'), default=1)
    product_id = fields.Many2one('product.product', string='Product', readonly=True, states={'draft': [('readonly', False)]}, domain=[('can_be_expensed', '=', True)])
    uom_id = fields.Many2one('product.uom', string='Unit of Measure', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.ref('product.product_uom_unit').id)
    analytic_account_id = fields.Many2one('account.analytic.account', readonly=True, states={'draft': [('readonly', False)]}, string='Contract')
    sequence = fields.Integer()
    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True, states={'draft': [('readonly', False)]}, required=True, default=lambda self: self.env['hr.employee'].search([('user_id', '=', self._uid)], limit=1).id)
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('confirm', 'Submitted'),
        ('accepted', 'Approved'),
        ('done', 'Waiting Payment'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled'),
        ],
        string='Status', readonly=True, track_visibility='onchange', copy=False, required=True, default='draft')
    expense_tax_id = fields.Many2many('account.tax', 'expense_line_tax', 'expense_line_id', 'tax_id', string='Taxes')
    note = fields.Text()

    @api.depends('unit_quantity', 'unit_amount', 'expense_tax_id')
    def _amount(self):
        for expense in self:
            expense.amount_untaxed = expense.unit_amount * expense.unit_quantity
            taxes = expense.expense_tax_id.compute_all(expense.unit_amount, expense.unit_quantity, expense.product_id, expense.employee_id.user_id.partner_id)
            expense.amount = taxes.get('total_included', False)

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.unit_amount = self.product_id.price_get('standard_price')[self.product_id.id]
            self.uom_id = self.product_id.uom_id.id

    @api.onchange('uom_id')
    def onchange_uom(self):
        res = {'value': {}}
        if self.product_id:
            if self.uom_id.category_id.id != self.product_id.uom_id.category_id.id:
                res['warning'] = {'title': _('Warning'), 'message': _('Selected Unit of Measure does not belong to the same category as the product Unit of Measure')}
                self.uom_id = self.product_id.uom_id.id
            return res

    @api.multi
    def unlink(self):
        for expense in self:
            if expense.state not in ['draft', 'cancel']:
                raise UserError(_('You can delete to submit or cancelled expenses!'))
        return super(HrExpense, self).unlink()

    @api.multi
    def _prepare_account_move_entry(self):
        AccountTax = self.env['account.tax']
        account_move = []
        for expense in self.filtered(lambda expense: expense.state == 'accepted'):
            if expense.product_id:
                account = expense.product_id.property_account_expense
                if not account:
                    account = expense.product_id.categ_id.property_account_expense_categ
                if not account:
                    raise UserError(_('No purchase account found for the product %s (or for his category), please configure one.') % (expense.product_id.name))
            else:
                account = self.env['ir.property'].with_context(force_company=expense.expense_id.company_id.id).get('property_account_expense_categ', 'product.category')
                if not account:
                    raise UserError(_('Please configure Default Expense account for Product purchase: `property_account_expense_categ`.'))

            move_line = {
                'type': 'src',
                'name': expense.name.split('\n')[0],
                'price_unit': expense.unit_amount,
                'quantity': expense.unit_quantity,
                'price': expense.amount_untaxed,
                'account_id': account.id,
                'product_id': expense.product_id.id,
                'uos_id': expense.uom_id.id,
                'account_analytic_id': expense.analytic_account_id.id,
            }
            account_move.append(move_line)
            tax_lines = []
            base_tax_amount = expense.amount_untaxed
            taxes = expense.expense_tax_id.compute_all(expense.unit_amount, expense.unit_quantity, expense.product_id, expense.employee_id.user_id.partner_id)['taxes']
            for tax in taxes:
                tax_code_id = tax['base_code_id']
                if not tax_code_id:
                    continue
                account_move[-1]['tax_code_id'] = tax_code_id
                is_price_include = AccountTax.browse(tax['id']).price_include
                if is_price_include:
                    ## We need to deduce the price for the tax
                    account_move[-1]['price'] = account_move[-1]['price'] - tax['amount']
                    # tax amount countains base amount without the tax
                    base_tax_amount = (base_tax_amount - tax['amount']) * tax['base_sign']
                else:
                    base_tax_amount = base_tax_amount * tax['base_sign']

                assoc_tax = {
                    'type': 'tax',
                    'name': tax['name'],
                    'price_unit': tax['price_unit'],
                    'quantity': 1,
                    'price': tax['amount'] or 0.0,
                    'account_id': tax['account_collected_id'] or move_line['account_id'],
                    'tax_code_id': tax['tax_code_id'],
                    'tax_amount': tax['amount'] * tax['base_sign'],
                }
                tax_lines.append(assoc_tax)
            account_move[-1]['tax_amount'] = expense.expense_id.currency_id.compute(base_tax_amount, expense.expense_id.company_id.currency_id)
            account_move += tax_lines
        return account_move

    @api.multi
    def approve_expenses(self):
        HrExpenseSheet = self.env['hr.expense.sheet']
        sheets = HrExpenseSheet.search([('state', 'in', ['draft', 'confirm', 'accepted']), ('employee_id', 'in', [expense.employee_id.id for expense in self if expense.state == 'confirm'])], order="id")
        exists_sheet = dict(map(lambda expense: (expense.employee_id.id, expense), sheets))
        for expense in self.filtered(lambda expense: expense.state in ['confirm']):
            current_sheet = exists_sheet.get(expense.employee_id.id, False)
            if not current_sheet:
                vals = {
                    'name': ("%s %s" % (_('Expenses for'), expense.employee_id.name)),
                    'employee_id': expense.employee_id.id,
                    'employee_payable_account_id': expense.employee_id.address_home_id.property_account_payable.id,
                    'department_id': expense.employee_id.department_id.id
                }
                current_sheet = HrExpenseSheet.create(vals)
                expense.write({'expense_id': current_sheet.id, 'state': 'accepted'})
                current_sheet.signal_workflow('confirm')
                exists_sheet[expense.employee_id.id] = current_sheet
            else:
                expense.write({'expense_id': current_sheet.id, 'state': 'accepted'})
                current_sheet.signal_workflow('confirm')
        map(lambda sheet: sheet.signal_workflow('validate'), exists_sheet.values())

    @api.multi
    def submit_expenses(self):
        expenses = self.filtered(lambda expense: expense.state in ['draft'])
        if len(expenses.ids) != len(self.ids):
            raise UserError(_('Expense you are trying to submit is already submitted!'))
        return self.write({'state': 'confirm'})

    @api.multi
    def cancel_expenses(self):
        partner_id = []
        for expense in self:
            body = (_('Your Expense %s has been cancelled.') % expense.name)
            expense.state = 'cancel'
            if expense.employee_id.user_id:
                partner_id.append(expense.employee_id.user_id.partner_id.id)
            expense.message_post(body=body, partner_ids=partner_id)

    @api.multi
    def done_expenses(self):
        return self.write({'state': 'done'})

    @api.multi
    def reset_expenses(self):
        return self.write({'state': 'draft', 'expense_id': False})
