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

from datetime import datetime
from openerp.osv import osv, fields


class sale_order(osv.osv):
    _inherit = 'sale.order'
    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
        'categ_ids': fields.many2many('crm.case.categ', 'sale_order_category_rel', 'order_id', 'category_id', 'Categories', \
            domain="['|',('section_id','=',section_id),('section_id','=',False), ('object_id.model', '=', 'crm.lead')]")
    }


class crm_case_section(osv.osv):
    _inherit = 'crm.case.section'

    def _get_sum_month_invoice(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, 0)
        obj = self.pool.get('account.invoice.report')
        when = datetime.today()
        for section_id in ids:
            invoice_ids = obj.search(cr, uid, [("section_id", "=", section_id), ('state', 'not in', ['draft', 'cancel']), ('year', '=', when.year), ('month', '=', when.month > 9 and when.month or "0%s" % when.month)], context=context)
            for invoice in obj.browse(cr, uid, invoice_ids, context=context):
                res[section_id] += invoice.price_total
        return res

    _columns = {
        'quotation_ids': fields.one2many('sale.order', 'section_id',
            string='Quotations', readonly=True,
            domain=[('state', 'in', ['draft', 'sent', 'cancel'])]),
        'sale_order_ids': fields.one2many('sale.order', 'section_id',
            string='Sale Orders', readonly=True,
            domain=[('state', 'not in', ['draft', 'sent', 'cancel'])]),
        'invoice_ids': fields.one2many('account.invoice', 'section_id',
            string='Invoices', readonly=True,
            domain=[('state', 'not in', ['draft', 'cancel'])]),
        'sum_month_invoice': fields.function(_get_sum_month_invoice,
            string='Total invoiced this month',
            type='integer', readonly=True),
    }


class res_users(osv.Model):
    _inherit = 'res.users'
    _columns = {
        'default_section_id': fields.many2one('crm.case.section', 'Default Sales Team'),
    }


class sale_crm_lead(osv.Model):
    _inherit = 'crm.lead'

    def on_change_user(self, cr, uid, ids, user_id, context=None):
        """ Override of on change user_id on lead/opportunity; when having sale
            the new logic is :
            - use user.default_section_id
            - or fallback on previous behavior """
        if user_id:
            user = self.pool.get('res.users').browse(cr, uid, user_id, context=context)
            if user.default_section_id and user.default_section_id.id:
                return {'value': {'section_id': user.default_section_id.id}}
        return super(sale_crm_lead, self).on_change_user(cr, uid, ids, user_id, context=context)


class account_invoice(osv.osv):
    _inherit = 'account.invoice'
    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
    }
    _defaults = {
        'section_id': lambda self, cr, uid, c=None: self.pool.get('res.users').browse(cr, uid, uid, c).default_section_id.id or False,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
