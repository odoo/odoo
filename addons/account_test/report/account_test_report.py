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

from openerp.osv import osv
from openerp.tools.translate import _
from openerp.report import report_sxw
from openerp.tools.safe_eval import safe_eval as eval


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
        def reconciled_inv():
            """
            returns the list of invoices that are set as reconciled = True
            """
            return self.pool.get('account.invoice').search(self.cr, self.uid, [('reconciled','=',True)])

        def order_columns(item, cols=None):
            """
            This function is used to display a dictionary as a string, with its columns in the order chosen.

            :param item: dict
            :param cols: list of field names
            :returns: a list of tuples (fieldname: value) in a similar way that would dict.items() do except that the
                returned values are following the order given by cols
            :rtype: [(key, value)]
            """
            if cols is None:
                cols = item.keys()
            return [(col, item.get(col)) for col in cols if col in item.keys()]

        localdict = {
            'cr': self.cr,
            'uid': self.uid,
            'reconciled_inv': reconciled_inv, #specific function used in different tests
            'result': None, #used to store the result of the test
            'column_order': None, #used to choose the display order of columns (in case you are returning a list of dict)
        }
        eval(code_exec, localdict, mode="exec", nocopy=True)
        result = localdict['result']
        column_order = localdict.get('column_order', None)

        if not isinstance(result, (tuple, list, set)):
            result = [result]
        if not result:
            result = [_('The test was passed successfully')]
        else:
            def _format(item):
                if isinstance(item, dict):
                    return ', '.join(["%s: %s" % (tup[0], tup[1]) for tup in order_columns(item, column_order)])
                else:
                    return item
            result = [_(_format(rec)) for rec in result]

        return result


class report_accounttest(osv.AbstractModel):
    _name = 'report.account_test.report_accounttest'
    _inherit = 'report.abstract_report'
    _template = 'account_test.report_accounttest'
    _wrapped_report_class = report_assert_account

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
