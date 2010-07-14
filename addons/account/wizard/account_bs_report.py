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

from osv import osv, fields
from tools.translate import _

class account_bs_report(osv.osv_memory):
    """
    This wizard will provide the account balance sheet report by periods, between any two dates.
    """
    _name = 'account.bs.report'
    _inherit = "account.common.report"
    _description = 'Account Balance Sheet Report'

    _columns = {
        'display_account': fields.selection([('bal_movement','With movements'),
                                             ('bal_solde','With balance is not equal to 0'),
                                             ('bal_all','All'),
                                             ],'Display accounts'),
        'display_type': fields.boolean("Landscape Mode"),
        'reserve_account_id': fields.many2one('account.account', 'Reserve & Surplus Account',required = True,
                                      help='This Account is used for trasfering Profit/Loss(If It is Profit : Amount will be added, Loss : Amount will be duducted.), Which is calculated from Profilt & Loss Report', domain = [('type','=','payable')]),
        }

    _defaults={
        'display_account': 'bal_all',
        'display_type': True,
        }

    def _check_date(self, cr, uid, data, context=None):
        if context is None:
            context = {}
        sql = """
            SELECT f.id, f.date_start, f.date_stop FROM account_fiscalyear f  Where %s between f.date_start and f.date_stop """
        cr.execute(sql,(data['form']['date_from'],))
        res = cr.dictfetchall()
        if res:

            if (data['form']['date_to'] > res[0]['date_stop'] or data['form']['date_to'] < res[0]['date_start']):
                raise  osv.except_osv(_('UserError'),_('Date to must be set between %s and %s') % (res[0]['date_start'], res[0]['date_stop']))
        else:
            raise osv.except_osv(_('UserError'),_('Date not in a defined fiscal year'))
        return True

    def _print_report(self, cr, uid, ids, data, query_line, context=None):
        if context is None:
            context = {}
        data['form'].update(self.read(cr, uid, ids, ['display_account',  'display_type', 'reserve_account_id'])[0])
        data['form']['query_line'] = query_line
        if data['form']['filter'] == 'filter_date':
           self._check_date(cr, uid, data, context=context)
        if data['form']['display_type']:
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'account.balancesheet.horizontal',
                'datas': data,
                'nodestroy':True,
                }
        else:
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'account.balancesheet',
                'datas': data,
                'nodestroy':True,
                }

account_bs_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: