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
from osv import fields, osv

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
        voucher_obj = self.pool.get('account.voucher')
        if context is None:
            context = {}
        voucher_ids = context.get('active_ids', [])
        number = int(self.browse(cr, uid, ids[0], context=context).check_number)
        if voucher_ids:
            checks = voucher_obj.browse(cr, uid, voucher_ids, context=context)
            for check in checks:
                voucher_obj.write(cr, uid, [check.id], {'number': str(number)}, context=context)
                number += 1

        check_layout_report = {
            'top' : 'account.print.check.top',
            'middle' : 'account.print.check.middle',
            'bottom' : 'account.print.check.bottom',
        }

        check_layout = voucher_obj.browse(cr, uid, voucher_ids[0], context=context).company_id.check_layout
        if not check_layout:
            check_layout = 'top'
        return {
            'type': 'ir.actions.report.xml', 
            'report_name':check_layout_report[check_layout],
            'datas': {
                'model':'account.voucher',
                'ids': voucher_ids,
                'report_type': 'pdf'
                },
            'nodestroy': True
            }

account_check_write()

