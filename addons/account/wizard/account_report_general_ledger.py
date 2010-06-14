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

from osv import fields, osv
from tools.translate import _
import tools

class account_report_general_ledger(osv.osv_memory):
    _inherit = "account.common.report"
    _name = "account.report.general.ledger"
    _description = "General Ledger Report"

    _columns = {
        'display_account': fields.selection([('bal_mouvement','With movements'), ('bal_all','All'), ('bal_solde','With balance is not equal to 0')],"Display accounts"),
        'landscape': fields.boolean("Landscape Mode"),
        'soldeinit': fields.boolean("Include initial balances"),
        'amount_currency': fields.boolean("With Currency"),
        #'state': fields.selection([('bydate','By Date'), ('byperiod','By Period'), ('all','By Date and Period'), ('none','No Filter')],"Date/Period Filter"),
    }

    _defaults = {
            'display_account' : 'bal_all',
            'landscape': True,
            'amount_currency' : True,
    }

    def _print_report(self, cr, uid, ids, context=None):
        if data['form']['landscape'] == True:
            return { 'type': 'ir.actions.report.xml', 'report_name': 'account.general.ledger_landscape', 'datas': data, 'nodestroy':True, }
        else:
            return { 'type': 'ir.actions.report.xml', 'report_name': 'account.general.ledger', 'datas': data, 'nodestroy':True, }


account_report_general_ledger()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
