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

from lxml import etree

from osv import fields, osv
from tools.translate import _

class account_report_general_ledger(osv.osv_memory):
    _inherit = "account.common.report"
    _name = "account.report.general.ledger"
    _description = "General Ledger Report"

    _columns = {
        'display_account': fields.selection([('bal_mouvement','With movements'), ('bal_all','All'), ('bal_solde','With balance is not equal to 0')],"Display accounts", required=True),
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

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        mod_obj = self.pool.get('ir.model.data')
        res = super(account_report_general_ledger, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
        if context.get('active_model', False) == 'account.account' and view_id:
            doc = etree.XML(res['arch'])
            nodes = doc.xpath("//field[@name='chart_account_id']")
            for node in nodes:
                node.set('readonly', '1')
                node.set('help', 'If you print the report from Account list/form view it will not consider Charts of account')
            res['arch'] = etree.tostring(doc)
        return res

    def _print_report(self, cr, uid, ids, data, query_line, context=None):
        if context is None:
            context = {}
        data['form'].update(self.read(cr, uid, ids, ['display_account',  'landscape',  'soldeinit', 'amount_currency', 'sortby'])[0])
        data['form']['query_line'] = query_line
        if data['form']['landscape']:
            return { 'type': 'ir.actions.report.xml', 'report_name': 'account.general.ledger_landscape', 'datas': data, 'nodestroy':True }
        return { 'type': 'ir.actions.report.xml', 'report_name': 'account.general.ledger', 'datas': data, 'nodestroy':True}

account_report_general_ledger()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: