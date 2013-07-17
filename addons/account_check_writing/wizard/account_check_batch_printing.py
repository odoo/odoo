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

from openerp.tools.translate import _

from openerp.osv import fields, osv

class account_check_write(osv.osv_memory):
    _name = 'account.check.write'
    _description = 'Prin Check in Batch'

    _columns = {
        'check_number': fields.integer('Next Check Number', required=True, help="The number of the next check number to be printed."),
    }

    def _get_next_number(self, cr, uid, context=None):
        dummy, sequence_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_check_writing', 'sequence_check_number')
        return self.pool.get('ir.sequence').read(cr, uid, sequence_id, ['number_next'])['number_next']

    _defaults = {
        'check_number': _get_next_number,
   }

    def print_check_write(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        voucher_obj = self.pool.get('account.voucher')
        ir_sequence_obj = self.pool.get('ir.sequence')

        #update the sequence to number the checks from the value encoded in the wizard
        dummy, sequence_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_check_writing', 'sequence_check_number')
        increment = ir_sequence_obj.read(cr, uid, sequence_id, ['number_increment'])['number_increment']
        new_value = self.browse(cr, uid, ids[0], context=context).check_number
        ir_sequence_obj.write(cr, uid, sequence_id, {'number_next': new_value})

        #validate the checks so that they get a number
        voucher_ids = context.get('active_ids', [])
        for check in voucher_obj.browse(cr, uid, voucher_ids, context=context):
            new_value += increment
            if check.number:
                raise osv.except_osv(_('Error!'),_("One of the printed check already got a number."))
        voucher_obj.proforma_voucher(cr, uid, voucher_ids, context=context)

        #update the sequence again (because the assignation using next_val was made during the same transaction of
        #the first update of sequence)
        ir_sequence_obj.write(cr, uid, sequence_id, {'number_next': new_value})

        #print the checks
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

