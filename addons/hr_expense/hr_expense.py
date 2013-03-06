# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time

from openerp import netsvc
from openerp.osv import fields, osv
from openerp.tools.translate import _

import openerp.addons.decimal_precision as dp

def _employee_get(obj, cr, uid, context=None):
    if context is None:
        context = {}
    ids = obj.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context)
    if ids:
        return ids[0]
    return False

class hr_expense_expense(osv.osv):

    def copy(self, cr, uid, id, default=None, context=None):
        if context is None:
            context = {}
        if not default: default = {}
        default.update({'voucher_id': False, 'date_confirm': False, 'date_valid': False, 'user_valid': False})
        return super(hr_expense_expense, self).copy(cr, uid, id, default, context=context)

    def _amount(self, cr, uid, ids, field_name, arg, context=None):
        res= {}
        for expense in self.browse(cr, uid, ids, context=context):
            total = 0.0
            for line in expense.line_ids:
                total += line.unit_amount * line.unit_quantity
            res[expense.id] = total
        return res

    def _get_currency(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, [uid], context=context)[0]
        if user.company_id:
            return user.company_id.currency_id.id
        else:
            return self.pool.get('res.currency').search(cr, uid, [('rate','=',1.0)], context=context)[0]

    _name = "hr.expense.expense"
    _inherit = ['mail.thread']
    _description = "Expense"
    _order = "id desc"
    _track = {
        'state': {
            'hr_expense.mt_expense_approved': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'accepted',
            'hr_expense.mt_expense_refused': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'cancelled',
            'hr_expense.mt_expense_confirmed': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'confirm',
        },
    }

    _columns = {
        'name': fields.char('Description', size=128, required=True, readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}),
        'id': fields.integer('Sheet ID', readonly=True),
        'date': fields.date('Date', select=True, readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}),
        'journal_id': fields.many2one('account.journal', 'Force Journal', help = "The journal used when the expense is done."),
        'employee_id': fields.many2one('hr.employee', "Employee", required=True, readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}),
        'user_id': fields.many2one('res.users', 'User', required=True),
        'date_confirm': fields.date('Confirmation Date', select=True, help="Date of the confirmation of the sheet expense. It's filled when the button Confirm is pressed."),
        'date_valid': fields.date('Validation Date', select=True, help="Date of the acceptation of the sheet expense. It's filled when the button Accept is pressed."),
        'user_valid': fields.many2one('res.users', 'Validation By', readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}),
        'account_move_id': fields.many2one('account.move', 'Ledger Posting'),
        'line_ids': fields.one2many('hr.expense.line', 'expense_id', 'Expense Lines', readonly=True, states={'draft':[('readonly',False)]} ),
        'note': fields.text('Note'),
        'amount': fields.function(_amount, string='Total Amount', digits_compute=dp.get_precision('Account')),
        'voucher_id': fields.many2one('account.voucher', "Employee's Receipt"),
        'currency_id': fields.many2one('res.currency', 'Currency', required=True, readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}),
        'department_id':fields.many2one('hr.department','Department', readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'state': fields.selection([
            ('draft', 'New'),
            ('cancelled', 'Refused'),
            ('confirm', 'Waiting Approval'),
            ('accepted', 'Approved'),
            ('done', 'Done'),
            ],
            'Status', readonly=True, track_visibility='onchange',
            help='When the expense request is created the status is \'Draft\'.\n It is confirmed by the user and request is sent to admin, the status is \'Waiting Confirmation\'.\
            \nIf the admin accepts it, the status is \'Accepted\'.\n If a receipt is made for the expense request, the status is \'Done\'.'),
    }
    _defaults = {
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'hr.employee', context=c),
        'date': fields.date.context_today,
        'state': 'draft',
        'employee_id': _employee_get,
        'user_id': lambda cr, uid, id, c={}: id,
        'currency_id': _get_currency,
    }

    def unlink(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.state != 'draft':
                raise osv.except_osv(_('Warning!'),_('You can only delete draft expenses!'))
        return super(hr_expense_expense, self).unlink(cr, uid, ids, context)

    def onchange_currency_id(self, cr, uid, ids, currency_id=False, company_id=False, context=None):
        res =  {'value': {'journal_id': False}}
        journal_ids = self.pool.get('account.journal').search(cr, uid, [('type','=','purchase'), ('currency','=',currency_id), ('company_id', '=', company_id)], context=context)
        if journal_ids:
            res['value']['journal_id'] = journal_ids[0]
        return res

    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        emp_obj = self.pool.get('hr.employee')
        department_id = False
        company_id = False
        if employee_id:
            employee = emp_obj.browse(cr, uid, employee_id, context=context)
            department_id = employee.department_id.id
            company_id = employee.company_id.id
        return {'value': {'department_id': department_id, 'company_id': company_id}}

    def expense_confirm(self, cr, uid, ids, context=None):
        for expense in self.browse(cr, uid, ids):
            if expense.employee_id and expense.employee_id.parent_id.user_id:
                self.message_subscribe_users(cr, uid, [expense.id], user_ids=[expense.employee_id.parent_id.user_id.id])
        return self.write(cr, uid, ids, {'state': 'confirm', 'date_confirm': time.strftime('%Y-%m-%d')}, context=context)

    def expense_accept(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'accepted', 'date_valid': time.strftime('%Y-%m-%d'), 'user_valid': uid}, context=context)

    def expense_canceled(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'cancelled'}, context=context)

    def action_receipt_create(self, cr, uid, ids, context=None):
        raise osv.except_osv(_('Error!'), _('Deprecated function used'))

    def account_move_get(self, cr, uid, expense_id, context=None):
        '''
        This method prepare the creation of the account move related to the given expense.

        :param expense_id: Id of voucher for which we are creating account_move.
        :return: mapping between fieldname and value of account move to create
        :rtype: dict
        '''
        journal_obj = self.pool.get('account.journal')
        expense = self.browse(cr, uid, expense_id, context=context)
        company_id = expense.company_id.id
        date = expense.date_confirm
        ref = expense.name
        journal_id = False
        if expense.journal_id:
            journal_id = expense.journal_id.id
        else:
            journal_id = journal_obj.search(cr, uid, [('type', '=', 'purchase'), ('company_id', '=', company_id)])
            if not journal_id:
                raise osv.except_osv(_('Error!'), _("No expense journal found. Please make sure you have a journal with type 'purchase' configured."))
            journal_id = journal_id[0]
        return self.pool.get('account.move').account_move_prepare(cr, uid, journal_id, date=date, ref=ref, company_id=company_id, context=context)

    def line_get_convert(self, cr, uid, x, part, date, context=None):
        #partner_id  = self.pool.get('res.partner')._find_partner(part)
        partner_id = part.id
        return {
            'date_maturity': x.get('date_maturity', False),
            'partner_id': partner_id,
            'name': x['name'][:64],
            'date': date,
            'debit': x['price']>0 and x['price'],
            'credit': x['price']<0 and -x['price'],
            'account_id': x['account_id'],
            'analytic_lines': x.get('analytic_lines', False),
            'amount_currency': x['price']>0 and abs(x.get('amount_currency', False)) or -abs(x.get('amount_currency', False)),
            'currency_id': x.get('currency_id', False),
            'tax_code_id': x.get('tax_code_id', False),
            'tax_amount': x.get('tax_amount', False),
            'ref': x.get('ref', False),
            'quantity': x.get('quantity',1.00),
            'product_id': x.get('product_id', False),
            'product_uom_id': x.get('uos_id', False),
            'analytic_account_id': x.get('account_analytic_id', False),
        }

    def compute_expense_totals(self, cr, uid, exp, company_currency, ref, account_move_lines, context=None):
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
        cur_obj = self.pool.get('res.currency')
        if context is None:
            context={}
        context.update({'date': exp.date_confirm or time.strftime('%Y-%m-%d')})
        total = 0.0
        total_currency = 0.0
        for i in account_move_lines:
            if exp.currency_id.id != company_currency:
                i['currency_id'] = exp.currency_id.id
                i['amount_currency'] = i['price']
                i['price'] = cur_obj.compute(cr, uid, exp.currency_id.id,
                        company_currency, i['price'],
                        context=context)
            else:
                i['amount_currency'] = False
                i['currency_id'] = False
            total -= i['price']
            total_currency -= i['amount_currency'] or i['price']
        return total, total_currency, account_move_lines


    def action_move_create(self, cr, uid, ids, context=None):
        move_obj = self.pool.get('account.move')
        if context is None:
            context = {}
        for exp in self.browse(cr, uid, ids, context=context):
            if not exp.employee_id.address_home_id:
                raise osv.except_osv(_('Error!'), _('The employee must have a home address.'))
            company_currency = exp.company_id.currency_id.id
            diff_currency_p = exp.currency_id.id <> company_currency
            
            #create the move that will contain the accounting entries
            move_id = move_obj.create(cr, uid, self.account_move_get(cr, uid, exp.id, context=context), context=context)
            #iml = self._get_analytic_lines
            
            # within: iml = self.pool.get('account.invoice.line').move_line_get
            iml = self.move_line_get(cr, uid, exp.id, context=context)
            
            # create one move line for the total
            total, total_currency, iml = self.compute_expense_totals(cr, uid, exp, company_currency, exp.name, iml, context=context)
            
            #counterline with the total on payable account for the employee
            acc = exp.employee_id.address_home_id.property_account_payable.id
            iml.append({
                    'type': 'dest',
                    'name': '/',
                    'price': total, 
                    'account_id': acc, 
                    'date_maturity': exp.date_confirm, 
                    'amount_currency': diff_currency_p and total_currency or False, 
                    'currency_id': diff_currency_p and exp.currency_id.id or False, 
                    'ref': exp.name
                    })
            
            lines = map(lambda x:(0,0,self.line_get_convert(cr, uid, x, exp.user_id.partner_id, exp.date_confirm, context=context)),iml)
            move_obj.write(cr, uid, [move_id], {'line_id': lines}, context=context)
            self.write(cr, uid, ids, {'account_move_id': move_id, 'state': 'done'}, context=context)
        return True

    def move_line_get(self, cr, uid, expense_id, context=None):
        res = []
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        if context is None:
            context = {}
        exp = self.browse(cr, uid, expense_id, context=context)
        company_currency = exp.company_id.currency_id.id

        for line in exp.line_ids:
            mres = self.move_line_get_item(cr, uid, line, context)
            if not mres:
                continue
            res.append(mres)
            tax_code_found= False
            
            #Calculate tax according to default tax on product
            
            #Taken from product_id_onchange in account.invoice
            if line.product_id:
                fposition_id = False
                fpos_obj = self.pool.get('account.fiscal.position')
                fpos = fposition_id and fpos_obj.browse(cr, uid, fposition_id, context=context) or False
                product = line.product_id
                taxes = product.supplier_taxes_id
                #If taxes are not related to the product, maybe they are in the account
                if not taxes:
                    a = product.property_account_expense.id #Why is not there a check here?
                    if not a:
                        a = product.categ_id.property_account_expense_categ.id
                    a = fpos_obj.map_account(cr, uid, fpos, a)
                    taxes = a and self.pool.get('account.account').browse(cr, uid, a, context=context).tax_ids or False
                tax_id = fpos_obj.map_tax(cr, uid, fpos, taxes)
            if not taxes:
                taxes = []
            #Calculating tax on the line and creating move?
            for tax in tax_obj.compute_all(cr, uid, taxes,
                    line.unit_amount ,
                    line.unit_quantity, line.product_id,
                    exp.user_id.partner_id)['taxes']:
                tax_code_id = tax['base_code_id']
                tax_amount = line.total_amount * tax['base_sign']
                if tax_code_found:
                    if not tax_code_id:
                        continue
                    res.append(self.move_line_get_item(cr, uid, line, context))
                    res[-1]['price'] = 0.0
                    res[-1]['account_analytic_id'] = False
                elif not tax_code_id:
                    continue
                tax_code_found = True
                res[-1]['tax_code_id'] = tax_code_id
                res[-1]['tax_amount'] = cur_obj.compute(cr, uid, exp.currency_id.id, company_currency, tax_amount, context={'date': exp.date_confirm})
                
                #Will create the tax here as we don't have the access 
                assoc_tax = {
                             'type':'tax',
                             'name':tax['name'],
                             'price_unit': tax['price_unit'],
                             'quantity': 1,
                             'price':  tax['amount'] * tax['base_sign'] or 0.0,
                             'account_id': tax['account_collected_id'],
                             'tax_code_id': tax['tax_code_id'],
                             'tax_amount': tax['amount'] * tax['base_sign'],
                             }
                res.append(assoc_tax)
        return res

    def move_line_get_item(self, cr, uid, line, context=None):
        company = line.expense_id.company_id
        property_obj = self.pool.get('ir.property')
        if line.product_id:
            acc = line.product_id.property_account_expense
            if not acc:
                acc = line.product_id.categ_id.property_account_expense_categ
        else:
            acc = property_obj.get(cr, uid, 'property_account_expense_categ', 'product.category', context={'force_company': company.id})
            if not acc:
                raise osv.except_osv(_('Error!'), _('Please configure Default Expense account for Product purchase: `property_account_expense_categ`.'))
        return {
            'type':'src',
            'name': line.name.split('\n')[0][:64],
            'price_unit':line.unit_amount,
            'quantity':line.unit_quantity,
            'price':line.total_amount,
            'account_id':acc.id,
            'product_id':line.product_id.id,
            'uos_id':line.uom_id.id,
            'account_analytic_id':line.analytic_account.id,
            #'taxes':line.invoice_line_tax_id,
        }

    def action_view_move(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display existing account.move of given expense ids.
        '''
        assert len(ids) == 1, 'This option should only be used for a single id at a time'
        voucher_id = self.browse(cr, uid, ids[0], context=context).voucher_id.id
        try:
            dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account', 'view_move_form')
        except:
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
            'res_id': account_move_id,
        }
        return result

hr_expense_expense()

class product_product(osv.osv):
    _inherit = "product.product"
    _columns = {
        'hr_expense_ok': fields.boolean('Can be Expensed', help="Specify if the product can be selected in an HR expense line."),
    }

product_product()

class hr_expense_line(osv.osv):
    _name = "hr.expense.line"
    _description = "Expense Line"

    def _amount(self, cr, uid, ids, field_name, arg, context=None):
        if not ids:
            return {}
        cr.execute("SELECT l.id,COALESCE(SUM(l.unit_amount*l.unit_quantity),0) AS amount FROM hr_expense_line l WHERE id IN %s GROUP BY l.id ",(tuple(ids),))
        res = dict(cr.fetchall())
        return res

    def _get_uom_id(self, cr, uid, context=None):
        result = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'product', 'product_uom_unit')
        return result and result[1] or False

    _columns = {
        'name': fields.char('Expense Note', size=128, required=True),
        'date_value': fields.date('Date', required=True),
        'expense_id': fields.many2one('hr.expense.expense', 'Expense', ondelete='cascade', select=True),
        'total_amount': fields.function(_amount, string='Total', digits_compute=dp.get_precision('Account')),
        'unit_amount': fields.float('Unit Price', digits_compute=dp.get_precision('Product Price')),
        'unit_quantity': fields.float('Quantities', digits_compute= dp.get_precision('Product Unit of Measure')),
        'product_id': fields.many2one('product.product', 'Product', domain=[('hr_expense_ok','=',True)]),
        'uom_id': fields.many2one('product.uom', 'Unit of Measure', required=True),
        'description': fields.text('Description'),
        'analytic_account': fields.many2one('account.analytic.account','Analytic account'),
        'ref': fields.char('Reference', size=32),
        'sequence': fields.integer('Sequence', select=True, help="Gives the sequence order when displaying a list of expense lines."),
        }
    _defaults = {
        'unit_quantity': 1,
        'date_value': lambda *a: time.strftime('%Y-%m-%d'),
        'uom_id': _get_uom_id,
    }
    _order = "sequence, date_value desc"

    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        res = {}
        if product_id:
            product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            res['name'] = product.name
            amount_unit = product.price_get('standard_price')[product.id]
            res['unit_amount'] = amount_unit
            res['uom_id'] = product.uom_id.id
        return {'value': res}

    def onchange_uom(self, cr, uid, ids, product_id, uom_id, context=None):
        res = {'value':{}}
        if not uom_id or not product_id:
            return res
        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        uom = self.pool.get('product.uom').browse(cr, uid, uom_id, context=context)
        if uom.category_id.id != product.uom_id.category_id.id:
            res['warning'] = {'title': _('Warning'), 'message': _('Selected Unit of Measure does not belong to the same category as the product Unit of Measure')}
            res['value'].update({'uom_id': product.uom_id.id})
        return res

hr_expense_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
