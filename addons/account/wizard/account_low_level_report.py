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

class accounting_report(osv.osv_memory):
    _name = "accounting.report"
    _inherit = "account.common.report"
    _description = "Accounting Report"

    _columns = {
        'enable_filter': fields.boolean('Enable Comparison'),
        'account_details': fields.boolean('Details by Account', help="Print Report with the account details."),
        'account_report_id': fields.many2one('account.report', 'Account Reports', required=True),
        'label_filter': fields.char('Column Label', size=32, help="This label will be displayed on report to show the balance computed for the given comparison filter."),
        'fiscalyear_id_cmp': fields.many2one('account.fiscalyear', 'Fiscal Year', help='Keep empty for all open fiscal year'),
        'filter_cmp': fields.selection([('filter_no', 'No Filters'), ('filter_date', 'Date'), ('filter_period', 'Periods')], "Filter by", required=True),
        'period_from_cmp': fields.many2one('account.period', 'Start Period'),
        'period_to_cmp': fields.many2one('account.period', 'End Period'),
        'date_from_cmp': fields.date("Start Date"),
        'date_to_cmp': fields.date("End Date"),
    }

    _defaults = {
            'filter_cmp': 'filter_no',
            'target_move': 'posted',
    }
    def _print_report(self, cr, uid, ids, data, context=None):
        #TODO: must read new fields, for comporison. Maybe better to do it at the end of check method
        data['form'].update(self.read(cr, uid, ids, ['account_report_id', 'enable_filter', 'account_details', 'label_filter'], context=context)[0])
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'accounting.report',
            'datas': data,
        }

accounting_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
