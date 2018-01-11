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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
