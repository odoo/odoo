# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from odoo import api, models, _
from odoo.tools.safe_eval import safe_eval
#
# Use period and Journal for selection or resources
#


class ReportAssertAccount(models.AbstractModel):
    _name = 'report.account_test.report_accounttest'
    _description = 'Account Test Report'

    @api.model
    def execute_code(self, code_exec):
        def reconciled_inv():
            """
            returns the list of invoices that are set as reconciled = True
            """
            return self.env['account.move'].search([('reconciled', '=', True)]).ids

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
                cols = list(item)
            return [(col, item.get(col)) for col in cols if col in item]

        localdict = {
            'cr': self.env.cr,
            'uid': self.env.uid,
            'reconciled_inv': reconciled_inv,  # specific function used in different tests
            'result': None,  # used to store the result of the test
            'column_order': None,  # used to choose the display order of columns (in case you are returning a list of dict)
            '_': _,
        }
        safe_eval(code_exec, localdict, mode="exec", nocopy=True)
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
            result = [_format(rec) for rec in result]

        return result

    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name('account_test.report_accounttest')
        records = self.env['accounting.assert.test'].browse(self.ids)
        return {
            'doc_ids': self._ids,
            'doc_model': report.model,
            'docs': records,
            'data': data,
            'execute_code': self.execute_code,
            'datetime': datetime
        }
