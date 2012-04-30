# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2010 OpenERP s.a. (<http://www.openerp.com>).
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

from osv import osv

"""Inherit res.currency to handle accounting date values when converting currencies"""

class res_currency_account(osv.osv):
    _inherit = "res.currency"

    def _get_conversion_rate(self, cr, uid, from_currency, to_currency, context=None):
        if context is None:
            context = {}
        rate = super(res_currency_account, self)._get_conversion_rate(cr, uid, from_currency, to_currency, context=context)
        account = context.get('res.currency.compute.account')
        account_invert = context.get('res.currency.compute.account_invert')
        if account and account.currency_mode == 'average' and account.currency_id:
            query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
            cr.execute('select sum(debit-credit),sum(amount_currency) from account_move_line l ' \
              'where l.currency_id=%s and l.account_id=%s and '+query, (account.currency_id.id,account.id,))
            tot1,tot2 = cr.fetchone()
            if tot2 and not account_invert:
                rate = float(tot1)/float(tot2)
            elif tot1 and account_invert:
                rate = float(tot2)/float(tot1)
        return rate

res_currency_account()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

