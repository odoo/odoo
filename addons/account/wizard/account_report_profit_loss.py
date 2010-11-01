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

class account_pl_report(osv.osv_memory):
    """
    This wizard will provide the account profit and loss report by periods, between any two dates.
    """
    _inherit = "account.common.account.report"
    _name = "account.pl.report"
    _description = "Account Profit And Loss Report"
    _columns = {
        'display_type': fields.boolean("Landscape Mode"),
    }

    _defaults = {
        'display_type': True,
        'journal_ids': [],
        'target_move': False
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        mod_obj = self.pool.get('ir.model.data')
        res = super(account_pl_report, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
        doc = etree.XML(res['arch'])
        nodes = doc.xpath("//field[@name='journal_ids']")
        for node in nodes:
            node.set('readonly', '1')
            node.set('required', '0')
        nodes = doc.xpath("//field[@name='target_move']")
        for node in nodes:
            node.set('readonly', '1')
            node.set('required', '0')
        res['arch'] = etree.tostring(doc)
        return res

    def _print_report(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        data = self.pre_print_report(cr, uid, ids, data, context=context)
        data['form'].update(self.read(cr, uid, ids, ['display_type'])[0])
        if data['form']['display_type']:
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'pl.account.horizontal',
                'datas': data,
            }
        else:
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'pl.account',
                'datas': data,
            }

account_pl_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: