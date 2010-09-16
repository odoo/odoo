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
        'initial_balance': fields.boolean('Include initial balances',
                                    help='It adds initial balance row on report which display previous sum amount of debit/credit/balance'),
        'reconcil': fields.boolean('Include Reconciled Entries', help='Consider reconciled entries'),
        'page_split': fields.boolean('One Partner Per Page', help='Display Ledger Report with One partner per page'),
        'amount_currency': fields.boolean("With Currency", help="It adds the currency column if the currency is different then the company currency"),
        'target_move': fields.selection([('all', 'All Entries'),
                                        ('posted', 'All Posted Entries')], 'Target Moves', required=True),

    }
    _defaults = {
       'reconcil': True,
       'initial_balance': True,
       'page_split': False,
       'target_move': 'all'
    }

    def _print_report(self, cr, uid, ids, data, query_line, context=None):
        if context is None:
            context = {}
        data = self.pre_print_report(cr, uid, ids, data, query_line, context=context)
        data['form'].update(self.read(cr, uid, ids, ['initial_balance', 'reconcil', 'page_split', 'amount_currency', 'target_move'])[0])
        if data['form']['page_split']:
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'account.third_party_ledger',
                'datas': data,
            }
        return {
                'type': 'ir.actions.report.xml',
                'report_name': 'account.third_party_ledger_other',
                'datas': data,
        }

account_partner_ledger()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: