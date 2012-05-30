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

from tools.translate import _

class hr_timesheet_invoice_factor(osv.osv):
    _name = "hr_timesheet_invoice.factor"
    _description = "Invoice Rate"
    _columns = {
        'name': fields.char('Internal name', size=128, required=True, translate=True),
        'customer_name': fields.char('Name', size=128, help="Label for the customer"),
        'factor': fields.float('Discount (%)', required=True, help="Discount in percentage"),
    }
    _defaults = {
        'factor': lambda *a: 0.0,
    }

hr_timesheet_invoice_factor()


class account_analytic_account(osv.osv):
    def _invoiced_calc(self, cr, uid, ids, name, arg, context=None):
        obj_invoice = self.pool.get('account.invoice')
        res = {}

        cr.execute('SELECT account_id as account_id, l.invoice_id '
                'FROM hr_analytic_timesheet h LEFT JOIN account_analytic_line l '
                    'ON (h.line_id=l.id) '
                    'WHERE l.account_id = ANY(%s)', (ids,))
        account_to_invoice_map = {}
        for rec in cr.dictfetchall():
            account_to_invoice_map.setdefault(rec['account_id'], []).append(rec['invoice_id'])

        for account in self.browse(cr, uid, ids, context=context):
            invoice_ids = filter(None, list(set(account_to_invoice_map.get(account.id, []))))
            for invoice in obj_invoice.browse(cr, uid, invoice_ids, context=context):
                res.setdefault(account.id, 0.0)
                res[account.id] += invoice.amount_untaxed
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)

        return res

    _inherit = "account.analytic.account"
    _columns = {
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist',
            help="The product to invoice is defined on the employee form, the price will be deduced by this pricelist on the product."),
        'amount_max': fields.float('Max. Invoice Price',
            help="Keep empty if this contract is not limited to a total fixed price."),
        'amount_invoiced': fields.function(_invoiced_calc, string='Invoiced Amount',
            help="Total invoiced"),
        'to_invoice': fields.many2one('hr_timesheet_invoice.factor', 'Timesheet Invocing Ratio',
            help="Fill this field if you plan to automatically generate invoices based " \
            "on the costs in this analytic account: timesheets, expenses, ..." \
            "You can configure an automatic invoice rate on analytic accounts."),
    }
    _defaults = {
        'pricelist_id': lambda self, cr, uid, ctx: ctx.get('pricelist_id', False),
    }
    def on_change_partner_id(self, cr, uid, ids,partner_id, context={}):
        res = super(account_analytic_account,self).on_change_partner_id(cr, uid, ids,partner_id, context=context)
        part = self.pool.get('res.partner').browse(cr, uid, partner_id,context=context)
        pricelist = part.property_product_pricelist and part.property_product_pricelist.id or False
        if pricelist:res['value']['pricelist_id'] = pricelist
        return res

    def set_close(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'close'}, context=context)

    def set_cancel(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'cancelled'}, context=context)

    def set_open(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'open'}, context=context)

    def set_pending(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'pending'}, context=context)

account_analytic_account()


class account_analytic_line(osv.osv):
    _inherit = 'account.analytic.line'
    _columns = {
        'invoice_id': fields.many2one('account.invoice', 'Invoice', ondelete="set null"),
        'to_invoice': fields.many2one('hr_timesheet_invoice.factor', 'Type of Invoicing', help="It allows to set the discount while making invoice"),
    }

    def unlink(self, cursor, user, ids, context=None):
        return super(account_analytic_line,self).unlink(cursor, user, ids,
                context=context)

    def write(self, cr, uid, ids, vals, context=None):
        self._check_inv(cr, uid, ids, vals)
        return super(account_analytic_line,self).write(cr, uid, ids, vals,
                context=context)

    def _check_inv(self, cr, uid, ids, vals):
        select = ids
        if isinstance(select, (int, long)):
            select = [ids]
        if ( not vals.has_key('invoice_id')) or vals['invoice_id' ] == False:
            for line in self.browse(cr, uid, select):
                if line.invoice_id:
                    raise osv.except_osv(_('Error !'),
                        _('You cannot modify an invoiced analytic line!'))
        return True

    def copy(self, cursor, user, obj_id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default.update({'invoice_id': False})
        return super(account_analytic_line, self).copy(cursor, user, obj_id,
                default, context=context)

account_analytic_line()


class hr_analytic_timesheet(osv.osv):
    _inherit = "hr.analytic.timesheet"
    def on_change_account_id(self, cr, uid, ids, account_id):
        res = {}
        if not account_id:
            return res
        res.setdefault('value',{})
        acc = self.pool.get('account.analytic.account').browse(cr, uid, account_id)
        st = acc.to_invoice.id
        res['value']['to_invoice'] = st or False
        if acc.state=='pending':
            res['warning'] = {
                'title': 'Warning',
                'message': 'The analytic account is in pending state.\nYou should not work on this account !'
            }
        return res

    def copy(self, cursor, user, obj_id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default.update({'invoice_id': False})
        return super(hr_analytic_timesheet, self).copy(cursor, user, obj_id,
                default, context=context)

hr_analytic_timesheet()

class account_invoice(osv.osv):
    _inherit = "account.invoice"

    def _get_analytic_lines(self, cr, uid, id, context=None):
        iml = super(account_invoice, self)._get_analytic_lines(cr, uid, id, context=context)

        inv = self.browse(cr, uid, [id], context=context)[0]
        if inv.type == 'in_invoice':
            obj_analytic_account = self.pool.get('account.analytic.account')
            for il in iml:
                if il['account_analytic_id']:
		    # *-* browse (or refactor to avoid read inside the loop)
                    to_invoice = obj_analytic_account.read(cr, uid, [il['account_analytic_id']], ['to_invoice'], context=context)[0]['to_invoice']
                    if to_invoice:
                        il['analytic_lines'][0][2]['to_invoice'] = to_invoice[0]
        return iml

account_invoice()

class account_move_line(osv.osv):
    _inherit = "account.move.line"

    def create_analytic_lines(self, cr, uid, ids, context=None):
        res = super(account_move_line, self).create_analytic_lines(cr, uid, ids,context=context)
        analytic_line_obj = self.pool.get('account.analytic.line')
        for move_line in self.browse(cr, uid, ids, context=context):
            for line in move_line.analytic_lines:
                toinv = line.account_id.to_invoice.id
                if toinv:
                    analytic_line_obj.write(cr, uid, line.id, {'to_invoice': toinv})
        return res

account_move_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

