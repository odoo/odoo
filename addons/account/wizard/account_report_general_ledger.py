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

class account_report_general_ledger(osv.osv_memory):
    _inherit = "account.common.account.report"
    _name = "account.report.general.ledger"
    _description = "General Ledger Report"

    _columns = {
        'landscape': fields.boolean("Landscape Mode"),
        'initial_balance': fields.boolean('Include Initial Balances',
                                    help='If you selected to filter by date or period, this field allow you to add a row to display the amount of debit/credit/balance that precedes the filter you\'ve set.'),
        'amount_currency': fields.boolean("With Currency", help="It adds the currency column if the currency is different then the company currency"),
        'sortby': fields.selection([('sort_date', 'Date'), ('sort_journal_partner', 'Journal & Partner')], 'Sort by', required=True),
    }
    _defaults = {
        'landscape': True,
        'amount_currency': True,
        'sortby': 'sort_date',
        'initial_balance': False,
    }

    def onchange_fiscalyear(self, cr, uid, ids, fiscalyear=False, context=None):
        res = {}
        if not fiscalyear:
            res['value'] = {'initial_balance': False}
        return res

    def _print_report(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        data = self.pre_print_report(cr, uid, ids, data, context=context)
        data['form'].update(self.read(cr, uid, ids, ['landscape',  'initial_balance', 'amount_currency', 'sortby'])[0])
        if not data['form']['fiscalyear_id']:# GTK client problem onchange does not consider in save record
            data['form'].update({'initial_balance': False})
        if data['form']['landscape']:
            return { 'type': 'ir.actions.report.xml', 'report_name': 'account.general.ledger_landscape', 'datas': data}
        return { 'type': 'ir.actions.report.xml', 'report_name': 'account.general.ledger', 'datas': data}

account_report_general_ledger()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
