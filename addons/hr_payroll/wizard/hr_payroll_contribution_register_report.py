# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime
from dateutil import relativedelta
from openerp.osv import fields, osv


class payslip_lines_contribution_register(osv.osv_memory):
    _name = 'payslip.lines.contribution.register'
    _description = 'PaySlip Lines by Contribution Registers'
    _columns = {
        'date_from': fields.date('Date From', required=True),
        'date_to': fields.date('Date To', required=True),
    }

    _defaults = {
        'date_from': lambda *a: time.strftime('%Y-%m-01'),
        'date_to': lambda *a: str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
    }

    def print_report(self, cr, uid, ids, context=None):
        datas = {
             'ids': context.get('active_ids', []),
             'model': 'hr.contribution.register',
             'form': self.read(cr, uid, ids, context=context)[0]
        }
        return self.pool['report'].get_action(
            cr, uid, [], 'hr_payroll.report_contributionregister', data=datas, context=context
        )
