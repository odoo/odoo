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
from operator import itemgetter

from osv import fields, osv
import ir

class account_fiscal_position(osv.osv):
    _name = 'account.fiscal.position'
    _description = 'Fiscal Position'
    _columns = {
        'name': fields.char('Fiscal Position', size=64, translate=True, required=True),
        'company_id': fields.many2one('res.company', 'Company'),
        'account_ids': fields.one2many('account.fiscal.position.account', 'position_id', 'Account Mapping'),
        'tax_ids': fields.one2many('account.fiscal.position.tax', 'position_id', 'Tax Mapping'),
        'note': fields.text('Notes', translate=True),
    }

    def map_tax(self, cr, uid, fposition_id, taxes, context={}):
        if not taxes:
            return []
        if not fposition_id:
            return map(lambda x: x.id, taxes)
        result = []
        for t in taxes:
            ok = False
            for tax in fposition_id.tax_ids:
                if tax.tax_src_id.id == t.id:
                    if tax.tax_dest_id:
                        result.append(tax.tax_dest_id.id)
                    ok=True
            if not ok:
                result.append(t.id)
        return result

    def map_account(self, cr, uid, fposition_id, account_id, context={}):
        if not fposition_id :
            return account_id
        for pos in fposition_id.account_ids:
            if pos.account_src_id.id==account_id:
                account_id = pos.account_dest_id.id
                break
        return account_id
account_fiscal_position()


class account_fiscal_position_tax(osv.osv):
    _name = 'account.fiscal.position.tax'
    _description = 'Fiscal Position Taxes Mapping'
    _rec_name = 'position_id'
    _columns = {
        'position_id': fields.many2one('account.fiscal.position', 'Fiscal Position', required=True, ondelete='cascade'),
        'tax_src_id': fields.many2one('account.tax', 'Tax Source', required=True),
        'tax_dest_id': fields.many2one('account.tax', 'Replacement Tax')
    }
account_fiscal_position_tax()


class account_fiscal_position_account(osv.osv):
    _name = 'account.fiscal.position.account'
    _description = 'Fiscal Position Accounts Mapping'
    _rec_name = 'position_id'
    _columns = {
        'position_id': fields.many2one('account.fiscal.position', 'Fiscal Position', required=True, ondelete='cascade'),
        'account_src_id': fields.many2one('account.account', 'Account Source', domain=[('type','<>','view')], required=True),
        'account_dest_id': fields.many2one('account.account', 'Account Destination', domain=[('type','<>','view')], required=True)
    }
account_fiscal_position_account()

class res_partner(osv.osv):
    _name = 'res.partner'
    _inherit = 'res.partner'
    _description = 'Partner'

    def _credit_debit_get(self, cr, uid, ids, field_names, arg, context):
        query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
        cr.execute("""SELECT l.partner_id, a.type, SUM(l.debit-l.credit)
                      FROM account_move_line l
                      LEFT JOIN account_account a ON (l.account_id=a.id)
                      WHERE a.type IN ('receivable','payable')
                      AND l.partner_id in %s
                      AND l.reconcile_id IS NULL
                      AND """ + query + """
                      GROUP BY l.partner_id, a.type
                      """,
                   (tuple(ids),))
        tinvert = {
            'credit': 'receivable',
            'debit': 'payable'
        }
        maps = {'receivable':'credit', 'payable':'debit' }
        res = {}
        for id in ids:
            res[id] = {}.fromkeys(field_names, 0)
        for pid,type,val in cr.fetchall():
            if val is None: val=0
            res[pid][maps[type]] = (type=='receivable') and val or -val
        return res

    def _asset_difference_search(self, cr, uid, obj, name, type, args,
                                 context=None):
        if not len(args):
            return []
        having_values = tuple(map(itemgetter(2), args))
        where = ' AND '.join(
            map(lambda x: '(SUM(debit-credit) %(operator)s %%s)' % {
                                'operator':x[1]},
                args))
        query = self.pool.get('account.move.line')._query_get(cr, uid,
                                                              context=context)
        cr.execute(('SELECT partner_id FROM account_move_line l '\
                    'WHERE account_id IN '\
                        '(SELECT id FROM account_account '\
                        'WHERE type=%s AND active) '\
                    'AND reconcile_id IS NULL '\
                    'AND '+query+' '\
                    'AND partner_id IS NOT NULL '\
                    'GROUP BY partner_id HAVING '+where),
                   (type,) + having_values)
        res = cr.fetchall()
        if not len(res):
            return [('id','=','0')]
        return [('id','in',map(itemgetter(0), res))]

    def _credit_search(self, cr, uid, obj, name, args, context):
        return self._asset_difference_search(
            cr, uid, obj, name, 'receivable', args, context=context)

    def _debit_search(self, cr, uid, obj, name, args, context):
        return self._asset_difference_search(
            cr, uid, obj, name, 'payable', args, context=context)

    _columns = {
        'credit': fields.function(_credit_debit_get,
            fnct_search=_credit_search, method=True, string='Total Receivable', multi='dc', help="Total amount this customer owes you."),
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
            help="This account will be used instead of the default one as the payable account for the current partner",
            required=True),
        'property_account_receivable': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Account Receivable",
            method=True,
            view_load=True,
            domain="[('type', '=', 'receivable')]",
            help="This account will be used instead of the default one as the receivable account for the current partner",
            required=True),
        'property_account_position': fields.property(
            'account.fiscal.position',
            type='many2one',
            relation='account.fiscal.position',
            string="Fiscal Position",
            method=True,
            view_load=True,
            help="The fiscal position will determine taxes and the accounts used for the the partner.",
        ),
        'property_payment_term': fields.property(
            'account.payment.term',
            type='many2one',
            relation='account.payment.term',
            string ='Payment Term',
            method=True,
            view_load=True,
            help="This payment term will be used instead of the default one for the current partner"),
        'ref_companies': fields.one2many('res.company', 'partner_id',
            'Companies that refers to partner'),
    }
res_partner()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

