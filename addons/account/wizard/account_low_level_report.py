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
        'account_report_id': fields.many2one('account.low.level.report', 'Account Reports', required=True),
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
    
    def _build_contexts_low(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        result = {}
        result['fiscalyear'] = 'fiscalyear_id_cmp' in data['form'] and data['form']['fiscalyear_id_cmp'] or False
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
        result['chart_account_id'] = 'chart_account_id' in data['form'] and data['form']['chart_account_id'] or False
        if data['form']['filter_cmp'] == 'filter_date':
            result['date_from'] = data['form']['date_from_cmp']
            result['date_to'] = data['form']['date_to_cmp']
        elif data['form']['filter_cmp'] == 'filter_period':
            if not data['form']['period_from_cmp'] or not data['form']['period_to_cmp']:
                raise osv.except_osv(_('Error'),_('Select a starting and an ending period'))
            result['period_from'] = data['form']['period_from_cmp']
            result['period_to'] = data['form']['period_to_cmp']
        return result
    
    def check_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {} 
        res = super(accounting_report, self).check_report(cr, uid, ids, context=context)
        data = {}
        data['form'] = self.read(cr, uid, ids, ['account_report_id', 'date_from_cmp',  'date_to_cmp',  'fiscalyear_id_cmp', 'journal_ids', 'period_from_cmp', 'period_to_cmp',  'filter_cmp',  'chart_account_id', 'target_move'], context=context)[0]
        for field in ['fiscalyear_id_cmp', 'chart_account_id', 'period_from_cmp', 'period_to_cmp', 'account_report_id']:
            if isinstance(data['form'][field], tuple):
                data['form'][field] = data['form'][field][0]
        comparison_context = self._build_contexts_low(cr, uid, ids, data, context=context)
#        data['form']['periods'] = comparison_context.get('periods', False) and comparison_context['periods'] or [] # Need to check
#        data['form']['comparison_context'] = comparison_context # Need to check
        res['datas']['form']['comparison_context'] = comparison_context
        return res

    def _print_report(self, cr, uid, ids, data, context=None):
        #TODO: must read new fields, for comporison. Maybe better to do it at the end of check method
        data['form'].update(self.read(cr, uid, ids, ['date_from_cmp',  'date_to_cmp',  'fiscalyear_id_cmp', 'period_from_cmp', 'period_to_cmp',  'filter_cmp', 'account_report_id', 'enable_filter', 'label_filter'], context=context)[0])
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'account.low.level.report',
            'datas': data,
        }

accounting_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
