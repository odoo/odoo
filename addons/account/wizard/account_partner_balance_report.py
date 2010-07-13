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

from tools.translate import _
from osv import fields, osv

class account_partner_balance(osv.osv_memory):
    """
    This wizard will provide the partner balance report by periods, between any two dates.
    """
    _inherit = 'account.common.partner.report'
    _name = 'account.partner.balance'
    _description = 'Print Account Partner Balance'

    _columns = {
        'soldeinit': fields.boolean('Include initial balances'),
                }
    _defaults={
       'soldeinit' : True,
                }

    def _check_date(self, cr, uid, data, context=None):
        sql = """
            SELECT f.id, f.date_start, f.date_stop FROM account_fiscalyear f  Where %s between f.date_start and f.date_stop """
        cr.execute(sql, (data['form']['date_from'],))
        res = cr.dictfetchall()
        if res:
            if (data['form']['date_to'] > res[0]['date_stop'] or data['form']['date_to'] < res[0]['date_start']):
                raise  osv.except_osv(_('UserError'),_('Date to must be set between %s and %s') % (str(res[0]['date_start']), str(res[0]['date_stop'])))
            else:
                return True
        else:
            raise osv.except_osv(_('UserError'),_('Date not in a defined fiscal year'))

    def _print_report(self, cr, uid, ids, data, query_line, context=None):
        if context is None:
            context = {}
        data = self.pre_print_report(cr, uid, ids, data, query_line, context=context)
        data['form'].update(self.read(cr, uid, ids, ['soldeinit'])[0])
        if data['form']['filter'] == 'filter_date':
            self._check_date(cr, uid, data, context)
        data['form']['query_line'] = query_line
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'account.partner.balance',
            'datas': data,
            'nodestroy': True,
                }

account_partner_balance()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: