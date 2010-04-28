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
import netsvc
from osv import fields, osv
import decimal_precision as dp

class account_budget_spread(osv.osv_memory):

    _name = 'account.budget.spread'
    _description = 'Account Budget spread '
    _columns = {
        'fiscalyear': fields.many2one('account.fiscalyear','Fiscal Year', required=True),
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Account')),
        }

    def check_spread(self, cr, uid, ids, context=None):
        service = netsvc.LocalService("object_proxy")
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, [])[0]
        res = service.execute(cr.dbname, uid, 'account.budget.post', 'spread', context['active_ids'], data['fiscalyear'], data['amount'])
        return {}

account_budget_spread()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: