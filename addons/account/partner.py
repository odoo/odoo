# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from osv import fields, osv
import ir

class res_partner(osv.osv):
    _name = 'res.partner'
    _inherit = 'res.partner'
    _description = 'Partner'
    def _credit_debit_get(self, cr, uid, ids, field_names, arg, context):
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
        cr.execute(("""select
                l.partner_id, a.type, sum(l.debit-l.credit)
            from
                account_move_line l
            left join
                account_account a on (l.account_id=a.id)
            where
                a.type in ('receivable','payable') and
                l.partner_id in (%s) and
                l.reconcile_id is null and
                """ % (','.join(map(str, ids)),))+query+"""
            group by
                l.partner_id, a.type
            """)
        tinvert = {
            'credit': 'receivable',
            'debit': 'payable'
        }
        maps = {'receivable':'credit', 'payable':'debit' }
        res = {}
        for id in ids:
            res[id] = {}.fromkeys(field_names, 0)
        for pid,type,val in cr.fetchall():
            res[pid][maps[type]] = val
        return res

    def _credit_search(self, cr, uid, obj, name, args):
        if not len(args):
            return []
        where = ' and '.join(map(lambda x: '(sum(debit-credit)'+x[1]+str(x[2])+')',args))
        query = self.pool.get('account.move.line')._query_get(cr, uid, context={})
        cr.execute(('select partner_id from account_move_line l where account_id in (select id from account_account where type=%s and active) and reconcile_id is null and '+query+' and partner_id is not null group by partner_id having '+where), ('receivable',) )
        res = cr.fetchall()
        if not len(res):
            return [('id','=','0')]
        return [('id','in',map(lambda x:x[0], res))]

    def _debit_search(self, cr, uid, obj, name, args):
        if not len(args):
            return []
        query = self.pool.get('account.move.line')._query_get(cr, uid, context={})
        where = ' and '.join(map(lambda x: '(sum(debit-credit)'+x[1]+str(x[2])+')',args))
        cr.execute(('select partner_id from account_move_line l where account_id in (select id from account_account where type=%s and active) and reconcile_id is null and '+query+' and partner_id is not null group by partner_id having '+where), ('payable',) )
        res = cr.fetchall()
        if not len(res):
            return [('id','=','0')]
        return [('id','in',map(lambda x:x[0], res))]

    _columns = {
        'credit': fields.function(_credit_debit_get, fnct_search=_credit_search, method=True, string='Total Receivable', multi='dc', help="Total amount this customer owns you."),
        'debit': fields.function(_credit_debit_get, fnct_search=_debit_search, method=True, string='Total Payable', multi='dc', help="Total amount you have to pay to this supplier."),
        'debit_limit': fields.float('Payable Limit'),
        'property_account_payable': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Account Payable",
            method=True,
            view_load=True,
            domain="[('type', '=', 'payable')]",
            help="This account will be used, instead of the default one, as the payable account for the current partner",
            required=True),
        'property_account_receivable': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Account Receivable",
            method=True,
            view_load=True,
            domain="[('type', '=', 'receivable')]",
            help="This account will be used, instead of the default one, as the receivable account for the current partner",
            required=True),
        'property_account_supplier_tax': fields.property(
            'account.tax',
            type='many2one',
            relation='account.tax',
            string="Default Supplier Tax",
            method=True,
            view_load=True,
            domain=[('parent_id','=',False)],
            help="This tax will be used, instead of the default one for supplier invoices."),
        'property_account_tax': fields.property(
            'account.tax',
            type='many2one',
            relation='account.tax',
            string="Default Tax",
            method=True,
            view_load=True,
            domain=[('parent_id','=',False)],
            help="This tax will be used, instead of the default one for customers."),
        'property_payment_term': fields.property(
            'account.payment.term',
            type='many2one',
            relation='account.payment.term',
            string ='Payment Term',
            method=True,
            view_load=True,
            help="This payment term will be used, instead of the default one, for the current partner"),
        'ref_companies': fields.one2many('res.company', 'partner_id',
            'Companies that refers to partner'),
    }
res_partner()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

