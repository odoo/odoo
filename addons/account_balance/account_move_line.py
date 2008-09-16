# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: account.py 1005 2005-07-25 08:41:42Z nicoe $
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

import time
import netsvc
from osv import fields, osv


class account_move_line(osv.osv):
    _name="account.move.line"
    _inherit="account.move.line"
    _description = "Entry lines"

    def _query_get(self, cr, uid, obj='l', context={}):
        query = super(account_move_line, self)._query_get(cr, uid, obj, context)
        if 'period_manner' in context:
            if context['period_manner'] == 'created':
                if 'periods' in context:
                    #the query have to be build with no reference to periods but thanks to the creation date
                    if context['periods']:
                        #if one or more period are given, use them
                        p_ids = self.pool.get('account.period').search(cr,uid,[('id','in',context['periods'])])
                    else:
                        #else we have to consider all the periods of the selected fiscal year(s)
                        fiscalyear_obj = self.pool.get('account.fiscalyear')
                        if not context.get('fiscalyear', False):

                            #if there is no fiscal year, take all the fiscal years
                            fiscalyear_ids = fiscalyear_obj.search(cr, uid, [('state', '=', 'draft')])
                        else:
                            fiscalyear_ids = [context['fiscalyear']]
                        p_ids = self.pool.get('account.period').search(cr,uid,[('fiscalyear_id','in',fiscalyear_ids)])

                    if p_ids == []:
                        return query

                    #remove from the old query the clause related to the period selection
                    res = ''
                    count = 1
                    clause_list = query.split('AND')
                    ref_string = ' '+obj+'.period_id in'
                    for clause in clause_list:
                        if count != 1 and not clause.startswith(ref_string):
                            res += "AND"
                        if not clause.startswith(ref_string):
                            res += clause
                            count += 1

                    #add to 'res' a new clause containing the creation date criterion
                    count = 1
                    res += " AND ("
                    periods = self.pool.get('account.period').read(cr,uid,p_ids,['date_start','date_stop'])
                    for period in periods:
                        if count != 1:
                            res += " OR "
                        #creation date criterion: the creation date of the move_line has to be 
                        # between the date_start and the date_stop of the selected periods
                        res += "("+obj+".create_date between to_date('" + period['date_start']  + "','yyyy-mm-dd') and to_date('" + period['date_stop']  + "','yyyy-mm-dd'))"
                        count += 1
                    res += ")"
                    return res
        return query
account_move_line()


class account_bank_statement_reconcile(osv.osv):
    _inherit = "account.bank.statement.reconcile"
    _columns = {
        'line_ids': fields.many2many('account.move.line', 'account_bank_statement_line_rel', 'statement_id', 'line_id', 'Entries'),
    }
account_bank_statement_reconcile()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

