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

        if not 'fiscalyear' in context:
            context['fiscalyear'] = self.pool.get('account.fiscalyear').find(cr, uid, exception=False)

        strQuery = ""
        if context.get('periods', False):
            ids = ','.join([str(x) for x in context['periods']])

            if not 'period_manner' in context:
                strQuery = obj+".active AND "+obj+".state<>'draft' AND "+obj+".period_id in (SELECT id from account_period WHERE fiscalyear_id=%d)" % (context['fiscalyear'],)
            else:
                if context['period_manner']=='actual':

                    strQuery = obj+".active AND "+obj+".state<>'draft' AND "+obj+".period_id in (SELECT id from account_period WHERE fiscalyear_id=%d AND id in (%s))" % (context['fiscalyear'], ids)
                else:
#                   p_id="in (SELECT id from account_period WHERE fiscalyear_id=%d AND id in (%s)))" % (context['fiscalyear'], ids)
                    strQuery = obj+".active AND "+obj+".state<>'draft' AND("

                    p_id=self.pool.get('account.period').search(cr,uid,[('fiscalyear_id','=',context['fiscalyear']),('id','in',context['periods'])])

                    periods = self.pool.get('account.period').read(cr,uid,p_id,['date_start','date_stop'])

                    count=1
                    len_periods=len(p_id)


                    for period in periods:
                        strQuery += "("+obj+".create_date between to_date('" + period['date_start']  + "','yyyy-mm-dd') and to_date('" + period['date_stop']  + "','yyyy-mm-dd'))"
                        if len_periods!=1 and count!=len_periods:
                            strQuery+=" OR "
                            count=count+1
                    if p_id==[]:
                        strQuery+=obj+".period_id in (SELECT id from account_period WHERE fiscalyear_id=%d))" % (context['fiscalyear'],)
                    else:
                        strQuery+=")"
        else:
            strQuery = obj+".active AND "+obj+".state<>'draft' AND "+obj+".period_id in (SELECT id from account_period WHERE fiscalyear_id=%d)" % (context['fiscalyear'],)

        return strQuery
account_move_line()


class account_bank_statement_reconcile(osv.osv):
    _inherit = "account.bank.statement.reconcile"
    _columns = {
        'line_ids': fields.many2many('account.move.line', 'account_bank_statement_line_rel', 'statement_id', 'line_id', 'Entries'),
    }
account_bank_statement_reconcile()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

