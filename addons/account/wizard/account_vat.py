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


class account_vat_declaration(osv.osv_memory):
    _name = 'account.vat.declaration'
    _description = 'Account Vat Declaration'
    _inherit = "account.common.report"
    _columns = {
        'based_on': fields.selection([('invoices', 'Invoices'),
                                      ('payments', 'Payments'),],
                                      'Based on', required=True),
        'chart_tax_id': fields.many2one('account.tax.code', 'Chart of Tax', help='Select Charts of Taxes', required=True, domain = [('parent_id','=', False)]),
        'display_detail': fields.boolean('Display Detail'),
    }

    def _get_tax(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        taxes = self.pool.get('account.tax.code').search(cr, uid, [('parent_id', '=', False), ('company_id', '=', user.company_id.id)], limit=1)
        return taxes and taxes[0] or False

    _defaults = {
        'based_on': 'invoices',
        'chart_tax_id': _get_tax
    }

    def create_vat(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'account.tax.code'
        datas['form'] = self.read(cr, uid, ids, context=context)[0]

        for field in datas['form'].keys():
            if isinstance(datas['form'][field], tuple):
                datas['form'][field] = datas['form'][field][0]

        taxcode_obj = self.pool.get('account.tax.code')
        taxcode_id = datas['form']['chart_tax_id']
        taxcode = taxcode_obj.browse(cr, uid, [taxcode_id], context=context)[0]
        datas['form']['company_id'] = taxcode.company_id.id

        return self.pool['report'].get_action(cr, uid, [], 'account.report_vat', data=datas, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
