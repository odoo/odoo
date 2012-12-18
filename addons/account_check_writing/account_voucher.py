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

from openerp.osv import osv,fields
from openerp.tools.translate import _
from openerp.tools.amount_to_text_en import amount_to_text
from lxml import etree

class account_voucher(osv.osv):
    _inherit = 'account.voucher'

    def _make_journal_search(self, cr, uid, ttype, context=None):
        if context is None: 
            context = {}
        journal_pool = self.pool.get('account.journal')
        if context.get('write_check',False) :
            return journal_pool.search(cr, uid, [('allow_check_writing', '=', True)], limit=1)
        return journal_pool.search(cr, uid, [('type', '=', ttype)], limit=1)

    _columns = {
        'amount_in_word' : fields.char("Amount in Word" , size=128, readonly=True, states={'draft':[('readonly',False)]}),
        'allow_check' : fields.related('journal_id', 'allow_check_writing', type='boolean', string='Allow Check Writing'),
        'number': fields.char('Number', size=32),
    }

    def onchange_amount(self, cr, uid, ids, amount, rate, partner_id, journal_id, currency_id, ttype, date, payment_rate_currency_id, company_id, context=None):
        """ Inherited - add amount_in_word and allow_check_writting in returned value dictionary """
        if not context:
            context = {}
        default = super(account_voucher, self).onchange_amount(cr, uid, ids, amount, rate, partner_id, journal_id, currency_id, ttype, date, payment_rate_currency_id, company_id, context=context)
        if 'value' in default:
            amount = 'amount' in default['value'] and default['value']['amount'] or amount

            #TODO : generic amount_to_text is not ready yet, otherwise language (and country) and currency can be passed
            #amount_in_word = amount_to_text(amount, context=context)
            amount_in_word = amount_to_text(amount)
            default['value'].update({'amount_in_word':amount_in_word})
            if journal_id:
                allow_check_writing = self.pool.get('account.journal').browse(cr, uid, journal_id, context=context).allow_check_writing
                default['value'].update({'allow_check':allow_check_writing})
        return default

    def print_check(self, cr, uid, ids, context=None):
        if not ids:
            return  {}

        check_layout_report = {
            'top' : 'account.print.check.top',
            'middle' : 'account.print.check.middle',
            'bottom' : 'account.print.check.bottom',
        }

        check_layout = self.browse(cr, uid, ids[0], context=context).company_id.check_layout
        return {
            'type': 'ir.actions.report.xml', 
            'report_name':check_layout_report[check_layout],
            'datas': {
                    'model':'account.voucher',
                    'id': ids and ids[0] or False,
                    'ids': ids and ids or [],
                    'report_type': 'pdf'
                },
            'nodestroy': True
            }

    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        """
            Add domain 'allow_check_writting = True' on journal_id field and remove 'widget = selection' on the same
            field because the dynamic domain is not allowed on such widget
        """
        if not context: context = {}
        res = super(account_voucher, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        nodes = doc.xpath("//field[@name='journal_id']")
        if context.get('write_check', False) :
            for node in nodes:
                node.set('domain', "[('type', '=', 'bank'), ('allow_check_writing','=',True)]")
                node.set('widget', '')
            res['arch'] = etree.tostring(doc)
        return res

account_voucher()
