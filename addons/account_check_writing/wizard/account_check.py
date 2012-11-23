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

import datetime
import time
import tools
from osv import fields, osv
from tools.translate import _

class account_check_write(osv.osv_memory):
    _name = 'account.check.write'
    _description = 'Take input as sequence and print report'
    _columns = {
        'check_number': fields.char('Check Number', required=True, help="This is the Check Number"),
    }

    _defaults = {
        'check_number': lambda obj, cr, uid, context:obj.pool.get('ir.sequence').get(cr, uid, 'account.check.write'),
   }
    def print_check_write(self, cr, uid, ids, context=None):
        if not ids:
            return  {}

        check_layout_report = {
            'top' : 'account.print.check.top',
            'middle' : 'account.print.check.middle',
            'bottom' : 'account.print.check.bottom',
        }
        check_layout = self.pool.get('account.voucher').browse(cr, uid, context['active_ids'], context=context)[0].company_id.check_layout
        return {
            'type': 'ir.actions.report.xml', 
            'report_name':check_layout_report[check_layout],
            'datas': {
                    'model':'account.voucher',
                    'id': context['active_ids'] and context['active_ids'][0] or False,
                    'ids': context['active_ids'] and context['active_ids'] or [],
                    'report_type': 'pdf'
                },
            'nodestroy': True
            }

account_check_write()

