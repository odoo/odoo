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

import datetime
import time
import re
from report import report_sxw
from itertools import groupby
from operator import itemgetter
from tools.translate import _
#
# Use period and Journal for selection or resources
#
class report_assert_account(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(report_assert_account, self).__init__(cr, uid, name, context=context)
        self.localcontext.update( {
            'time': time,
            'datetime': datetime,
            'execute_code': self.execute_code,
        })

    def execute_code(self, code_exec):
        def group(lst, col):
            return dict((k, [v for v in itr]) for k, itr in groupby(sorted(lst, key=lambda x: x[col]), itemgetter(col)))

        #TODO what is this method used for, name unclear and doesn't seem to be used
        def sort_by_intified_num(a, b):
            if a is None:
                return -1
            elif b is None:
                return 1
            else:
                #if a is not None and b is not None:
                return cmp(int(a), int(b))

        def reconciled_inv():
            reconciled_inv_ids = self.pool.get('account.invoice').search(self.cr, self.uid, [('reconciled','=',True)])
            return reconciled_inv_ids

        def get_parent(acc_id):
            acc_an_id = self.pool.get('account.analytic.account').browse(self.cr, self.uid, acc_id).parent_id
            while acc_an_id.parent_id:
                acc_an_id = acc_an_id.parent_id
            return acc_an_id.id

        def order_columns(item, cols=None):
            if cols is None:
                cols = item.keys()
            return [(col, item.get(col)) for col in cols if col in item.keys()]

        localdict = {
            'cr': self.cr,
            '_': _,
            'reconciled_inv' : reconciled_inv,
            'group' : group,
            'get_parent' : get_parent,
            'now': datetime.datetime.now(),
            'result': None,
            'column_order': None,
        }

        exec code_exec in localdict

        result = localdict['result']
        column_order = localdict.get('column_order', None)

        if not isinstance(result, (tuple, list, set)):
            result = [result]

        if not result:
            result = [_('The test was passed successfully')]
        #TODO: not sure this condition is needed, it is only a subcategory of the final else
        elif all([isinstance(x, dict) for x in result]):
            result = [', '.join(["%s: %s" % (k, v) for k, v in order_columns(rec, column_order)]) for rec in result]
        else:
            def _format(a):
                if isinstance(a, dict):
                    return ', '.join(["%s: %s" % (tup[0], tup[1]) for tup in order_columns(a, column_order)])
                else:
                    return a
            result = [_format(rec) for rec in result]

        return result

report_sxw.report_sxw('report.account.test.assert.print', 'accounting.assert.test', 'addons/account_test/report/account_test.rml', parser=report_assert_account, header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
