# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv

from tools.translate import _

class hr_timesheet_invoice_factor(osv.osv):
    _name = "hr_timesheet_invoice.factor"
    _description = "Invoice rate"
    _columns = {
        'name': fields.char('Internal name', size=128, required=True),
        'customer_name': fields.char('Visible name', size=128),
        'factor': fields.float('Discount (%)', required=True),
    }
    _defaults = {
        'factor': lambda *a: 0.0,
    }

hr_timesheet_invoice_factor()


class account_analytic_account(osv.osv):
    def _invoiced_calc(self, cr, uid, ids, name, arg, context={}):
        res = {}
        for account in self.browse(cr, uid, ids):
            invoiced = {}
            cr.execute('select distinct(l.invoice_id) from hr_analytic_timesheet h left join account_analytic_line l on (h.line_id=l.id) where account_id=%s', (account.id,))
            invoice_ids = filter(None, map(lambda x: x[0], cr.fetchall()))
            for invoice in self.pool.get('account.invoice').browse(cr, uid, invoice_ids, context):
                res.setdefault(account.id, 0.0)
                res[account.id] += invoice.amount_untaxed
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    _inherit = "account.analytic.account"
    _columns = {
        'pricelist_id' : fields.many2one('product.pricelist', 'Sale Pricelist'),
        'amount_max': fields.float('Max. Invoice Price'),
        'amount_invoiced': fields.function(_invoiced_calc, method=True, string='Invoiced Amount',
            help="Total invoiced"),
        'to_invoice': fields.many2one('hr_timesheet_invoice.factor','Reinvoice Costs',
            help="Check this field if you plan to automatically generate invoices based " \
            "on the costs in this analytic account: timesheets, expenses, ..." \
            "You can configure an automatic invoice rate on analytic accounts."),
    }
    _defaults = {
        'pricelist_id': lambda self,cr, uid, ctx: ctx.get('pricelist_id', False),
    }
account_analytic_account()


class account_analytic_line(osv.osv):
    _inherit = 'account.analytic.line'
    _columns = {
        'invoice_id': fields.many2one('account.invoice', 'Invoice'),
        'to_invoice': fields.many2one('hr_timesheet_invoice.factor', 'Invoicing'),
    }

    def unlink(self, cursor, user, ids, context=None):
        self._check(cursor, user, ids)
        return super(account_analytic_line,self).unlink(cursor, user, ids,
                context=context)

    def write(self, cr, uid, ids, vals, context=None):
        self._check(cr, uid, ids)
        return super(account_analytic_line,self).write(cr, uid, ids, vals,
                context=context)

    def _check(self, cr, uid, ids):
        select = ids
        if isinstance(select, (int, long)):
            select = [ids]
        for line in self.browse(cr, uid, select):
            if line.invoice_id:
                raise osv.except_osv(_('Error !'),
                        _('You can not modify an invoiced analytic line!'))
        return True

    def copy(self, cursor, user, obj_id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default.update({'invoice_id': False})
        return super(account_analytic_line, self).copy(cursor, user, obj_id,
                default, context)

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
                default, context)

hr_analytic_timesheet()

class account_invoice(osv.osv):
    _inherit = "account.invoice"

    def _get_analytic_lines(self, cr, uid, id):
        iml = super(account_invoice, self)._get_analytic_lines(cr, uid, id)

        inv = self.browse(cr, uid, [id])[0]
        if inv.type == 'in_invoice':
            for il in iml:
                if il['account_analytic_id']:
                    to_invoice = self.pool.get('account.analytic.account').read(cr, uid, [il['account_analytic_id']], ['to_invoice'])[0]['to_invoice']
                    if to_invoice:
                        il['analytic_lines'][0][2]['to_invoice'] = to_invoice[0]
        return iml

account_invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

