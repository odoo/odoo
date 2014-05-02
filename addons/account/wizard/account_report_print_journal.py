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

from openerp.osv import fields, osv
from lxml import etree


class account_print_journal(osv.osv_memory):
    _inherit = "account.common.journal.report"
    _name = 'account.print.journal'
    _description = 'Account Print Journal'

    _columns = {
        'sort_selection': fields.selection([('l.date', 'Date'),
                                            ('am.name', 'Journal Entry Number'),],
                                            'Entries Sorted by', required=True),
        'journal_ids': fields.many2many('account.journal', 'account_print_journal_journal_rel', 'account_id', 'journal_id', 'Journals', required=True),
    }

    _defaults = {
        'sort_selection': 'am.name',
        'filter': 'filter_period',
        'journal_ids': False,
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        '''
        used to set the domain on 'journal_ids' field: we exclude or only propose the journals of type 
        sale/purchase (+refund) accordingly to the presence of the key 'sale_purchase_only' in the context.
        '''
        if context is None: 
            context = {}
        res = super(account_print_journal, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])

        if context.get('sale_purchase_only'):
            domain ="[('type', 'in', ('sale','purchase','sale_refund','purchase_refund'))]"
        else:
            domain ="[('type', 'not in', ('sale','purchase','sale_refund','purchase_refund'))]"
        nodes = doc.xpath("//field[@name='journal_ids']")
        for node in nodes:
            node.set('domain', domain)
        res['arch'] = etree.tostring(doc)
        return res

    def _print_report(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        data = self.pre_print_report(cr, uid, ids, data, context=context)
        data['form'].update(self.read(cr, uid, ids, ['sort_selection'], context=context)[0])
        if context.get('sale_purchase_only'):
            return self.pool['report'].get_action(cr, uid, [], 'account.report_salepurchasejournal', data=data, context=context)
        else:
            return self.pool['report'].get_action(cr, uid, [], 'account.report_journal', data=data, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
