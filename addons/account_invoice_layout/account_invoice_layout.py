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

from osv import fields, osv

class notify_message(osv.osv):
    _name = 'notify.message'
    _description = 'Notify By Messages'
    _columns = {
        'name':  fields.char('Title', size=64, required=True),
        'msg': fields.text('Special Message', size=128, required=True, help='This notification will appear at the bottom of the Invoices when printed.', translate=True)
    }

notify_message()

class account_invoice_line(osv.osv):

    def move_line_get_item(self, cr, uid, line, context=None):
        if line.state != 'article':
            return None
        return super(account_invoice_line, self).move_line_get_item(cr, uid, line, context)

    def fields_get(self, cr, uid, fields=None, context=None):
        article = {
            'article': [('readonly', False), ('invisible', False)],
            'text': [('readonly', True), ('invisible', True), ('required', False)],
            'subtotal': [('readonly', True), ('invisible', True), ('required', False)],
            'title': [('readonly', True), ('invisible', True), ('required', False)],
            'break': [('readonly', True), ('invisible', True), ('required', False)],
            'line': [('readonly', True), ('invisible', True), ('required', False)],
        }
        states = {
            'name': {
                'break': [('readonly', True),('required', False),('invisible', True)],
                'line': [('readonly', True),('required', False),('invisible', True)],
                },
            'product_id': article,
            'account_id': article,
            'quantity': article,
            'uos_id': article,
            'price_unit': article,
            'discount': article,
            'invoice_line_tax_id': article,
            'account_analytic_id': article,
        }
        res = super(account_invoice_line, self).fields_get(cr, uid, fields, context)
        for field in res:
            if states.has_key(field):
                for key,value in states[field].items():
                    res[field].setdefault('states',{})
                    res[field]['states'][key] = value
        return res

    def onchange_invoice_line_view(self, cr, uid, id, type, context=None, *args):

        if (not type):
            return {}
        if type != 'article':
            temp = {'value': {
                    'product_id': False,
                    'uos_id': False,
                    'account_id': False,
                    'price_unit': False,
                    'price_subtotal': False,
                    'quantity': 0,
                    'discount': False,
                    'invoice_line_tax_id': False,
                    'account_analytic_id': False,
                    },
                }
            if type == 'line':
                temp['value']['name'] = ' '
            if type == 'break':
                temp['value']['name'] = ' '
            if type == 'subtotal':
                temp['value']['name'] = 'Sub Total'
            return temp
        return {}

    def create(self, cr, user, vals, context=None):
        if vals.has_key('state'):
            if vals['state'] == 'line':
                vals['name'] = ' '
            if vals['state'] == 'break':
                vals['name'] = ' '
            if vals['state'] != 'article':
                vals['quantity']= 0
                vals['account_id']= self._default_account(cr, user, None)
        return super(account_invoice_line, self).create(cr, user, vals, context)

    def write(self, cr, user, ids, vals, context=None):
        if vals.has_key('state'):
            if vals['state'] != 'article':
                vals['product_id']= False
                vals['uos_id']= False
                vals['account_id']= self._default_account(cr, user, None)
                vals['price_unit']= False
                vals['price_subtotal']= False
                vals['quantity']= 0
                vals['discount']= False
                vals['invoice_line_tax_id']= False
                vals['account_analytic_id']= False
            if vals['state'] == 'line':
                vals['name'] = ' '
            if vals['state'] == 'break':
                vals['name'] = ' '
        return super(account_invoice_line, self).write(cr, user, ids, vals, context)

    def copy_data(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default['state'] = self.browse(cr, uid, id, context=context).state
        return super(account_invoice_line, self).copy_data(cr, uid, id, default, context)

    def _fnct(self, cr, uid, ids, name, args, context=None):
        res = {}
        lines = self.browse(cr, uid, ids, context=context)
        account_ids = [line.account_id.id for line in lines]
        account_names = dict(self.pool.get('account.account').name_get(cr, uid, account_ids, context=context))
        for line in lines:
            if line.state != 'article':
                if line.state == 'line':
                    res[line.id] = '-----------------------------------------'
                elif line.state == 'break':
                    res[line.id] = 'PAGE BREAK'
                else:
                    res[line.id] = ' '
            else:
                res[line.id] = account_names.get(line.account_id.id, '')
        return res

    _name = "account.invoice.line"
    _order = "invoice_id, sequence asc"
    _description = "Invoice Line"
    _inherit = "account.invoice.line"
    _columns = {
        'state': fields.selection([
                ('article','Product'),
                ('title','Title'),
                ('text','Note'),
                ('subtotal','Sub Total'),
                ('line','Separator Line'),
                ('break','Page Break'),]
            ,'Type', select=True, required=True),
        'sequence': fields.integer('Sequence Number', help="Gives the sequence order when displaying a list of invoice lines."),
        'functional_field': fields.function(_fnct, arg=None, fnct_inv=None, fnct_inv_arg=None, type='char', fnct_search=None, obj=None, store=False, string="Source Account"),
    }

    def _default_account(self, cr, uid, context=None):
        cr.execute("select id from account_account where parent_id IS NULL LIMIT 1")
        res = cr.fetchone()
        return res[0]

    _defaults = {
        'state': 'article',
        'sequence': 0,
    }

account_invoice_line()

class one2many_mod2(fields.one2many):

    def get(self, cr, obj, ids, name, user=None, offset=0, context=None, values=None):
        if context is None:
            context = {}
        if not values:
            values = {}
        res = {}
        for id in ids:
            res[id] = []
        ids2 = obj.pool.get(self._obj).search(cr, user, [(self._fields_id,'in',ids),('state','=','article')], limit=self._limit)
        for r in obj.pool.get(self._obj)._read_flat(cr, user, ids2, [self._fields_id], context=context, load='_classic_write'):
            res[r[self._fields_id]].append( r['id'] )
        return res

class account_invoice(osv.osv):

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default['invoice_line'] = False
        return super(account_invoice, self).copy(cr, uid, id, default, context)

    _inherit = "account.invoice"
    _columns = {
        'abstract_line_ids': fields.one2many('account.invoice.line', 'invoice_id', 'Invoice Lines',readonly=True, states={'draft':[('readonly',False)]}),
        'invoice_line': one2many_mod2('account.invoice.line', 'invoice_id', 'Invoice Lines',readonly=True, states={'draft':[('readonly',False)]}),
    }

account_invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
