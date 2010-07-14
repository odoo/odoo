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

class account_partner_ledger(osv.osv_memory):
    """
    This wizard will provide the partner Ledger report by periods, between any two dates.
    """
    _name = 'account.partner.ledger'
    _inherit = 'account.common.partner.report'
    _description = 'Account Partner Ledger'
    _columns = {
        'soldeinit': fields.boolean('Include initial balances'),
        'reconcil': fields.boolean('Include Reconciled Entries'),
        'page_split': fields.boolean('One Partner Per Page'),
        'amount_currency': fields.boolean("With Currency", help='Print report with currency column'),
                }
    _defaults = {
       'reconcile' : True,
       'soldeinit' : True,
       'page_split' : False,
               }

    def _check_date(self, cr, uid, data, context=None):
        if context is None:
            context = {}
        sql = """
            SELECT f.id, f.date_start, f.date_stop FROM account_fiscalyear f  Where %s between f.date_start and f.date_stop """
        cr.execute(sql, (data['form']['date_from'],))
        res = cr.dictfetchall()
        if res:
            if (data['form']['date_to'] > res[0]['date_stop'] or data['form']['date_to'] < res[0]['date_start']):
                raise osv.except_osv(_('UserError'),_('Date to must be set between %s and %s') % (str(res[0]['date_start']), str(res[0]['date_stop'])))
        else:
            raise osv.except_osv(_('UserError'),_('Date not in a defined fiscal year'))
        return True

    def _print_report(self, cr, uid, ids, data, query_line, context=None):
        if context is None:
            context = {}
        data = self.pre_print_report(cr, uid, ids, data, query_line, context=context)
        data['form'].update(self.read(cr, uid, ids, ['soldeinit', 'reconcil', 'page_split', 'amount_currency'])[0])
        if data['form']['filter'] == 'filter_date':
            self._check_date(cr, uid, data, context)
        if data['form']['page_split']:
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'account.third_party_ledger',
                'datas': data,
                'nodestroy':True,
                    }
        return {
                'type': 'ir.actions.report.xml',
                'report_name': 'account.third_party_ledger_other',
                'datas': data,
                'nodestroy':True,
                }

account_partner_ledger()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
