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

from osv import osv, fields
from tools.translate import _

class account_balance_report(osv.osv_memory):
    _inherit = "account.common.report"
    _name = 'account.balance.report'
    _description = 'Account Balance Report'
    _columns = {
        'display_account': fields.selection([('bal_all','All'), ('bal_mouvement','With movements'),
                         ('bal_solde','With balance is not equal to 0'),
                         ],'Display accounts', required=True),
                }

    _defaults = {
        'display_account': 'bal_all'
                }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        mod_obj = self.pool.get('ir.model.data')
        res = super(account_balance_report, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
        if context.get('active_model', False) == 'account.account' and view_id:
            doc = etree.XML(res['arch'])
            nodes = doc.xpath("//field[@name='chart_account_id']")
            for node in nodes:
                node.set('readonly', '1')
                node.set('help', 'If you print the report from Account list/form view it will not consider Charts of account')
            res['arch'] = etree.tostring(doc)
        return res

    def _print_report(self, cr, uid, ids, data, query_line, context=None):
        data['form'].update(self.read(cr, uid, ids, ['display_account'])[0])
        data['form']['query_line'] = query_line
        return {'type': 'ir.actions.report.xml', 'report_name': 'account.account.balance', 'datas': data, 'nodestroy':True}

account_balance_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
