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
from tools.translate import _

class account_report_general_ledger(osv.osv_memory):
    _inherit = "account.common.report"
    _name = "account.report.general.ledger"
    _description = "General Ledger Report"

    _columns = {
        'display_account': fields.selection([('bal_all','All'), ('bal_mouvement','With movements'),
                         ('bal_solde','With balance is not equal to 0'),
                         ],'Display accounts', required=True),
        'landscape': fields.boolean("Landscape Mode"),
        'soldeinit': fields.boolean("Include initial balances"),
        'amount_currency': fields.boolean("With Currency"),
        'sortby': fields.selection([('sort_date', 'Date'), ('sort_journal_partner', 'Journal & Partner')], 'Sort By', required=True),
                }
    _defaults = {
            'display_account': 'bal_all',
            'landscape': True,
            'amount_currency': True,
            'sortby': 'sort_date',
                }

    def _print_report(self, cr, uid, ids, data, query_line, context=None):
        if context is None:
            context = {}
        data['form'].update(self.read(cr, uid, ids, ['display_account',  'landscape',  'soldeinit', 'amount_currency', 'sortby'])[0])
        if data['form']['landscape']:
            return { 'type': 'ir.actions.report.xml', 'report_name': 'account.general.ledger_landscape', 'datas': data, 'nodestroy':True }
        return { 'type': 'ir.actions.report.xml', 'report_name': 'account.general.ledger', 'datas': data, 'nodestroy':True}

account_report_general_ledger()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: