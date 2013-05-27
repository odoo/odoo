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

from datetime import date, datetime
from openerp import tools
from dateutil.relativedelta import relativedelta
from openerp.osv import osv, fields


class sale_order(osv.osv):
    _inherit = 'sale.order'
    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
        'categ_ids': fields.many2many('crm.case.categ', 'sale_order_category_rel', 'order_id', 'category_id', 'Categories', \
            domain="['|',('section_id','=',section_id),('section_id','=',False), ('object_id.model', '=', 'crm.lead')]")
    }

    def _make_invoice(self, cr, uid, order, lines, context=None):
        if order.section_id:
            context = dict(context or {}, default_section_id= order.section_id.id)
        return super(sale_order, self)._make_invoice(cr, uid, order, lines, context=context)

    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        invoice_vals = super(sale_order, self)._prepare_invoice(cr, uid, order, lines, context=context)
        if order.section_id and order.section_id.id:
            invoice_vals['section_id'] = order.section_id.id
        return invoice_vals


class crm_case_section(osv.osv):
    _inherit = 'crm.case.section'

    def _get_created_quotation_per_duration(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, [])
        obj = self.pool.get('sale.order')
        today = date.today().replace(day=1)
        begin = (today + relativedelta(months=-5)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        for section in self.browse(cr, uid, ids, context=context):
            domain = [("section_id", "=", section.id), ('state', 'in', ['draft', 'sent']), ('date_order', '>=', begin)]
            group_obj = obj.read_group(cr, uid, domain, ['amount_total', "date_order"], "date_order", context=context)
            group_list = [group['amount_total'] for group in group_obj]
            nb_month = group_obj and relativedelta(today, datetime.strptime(group_obj[-1]['__domain'][0][2], '%Y-%m-%d')).months or 0
            res[section.id] = [0]*(5 - len(group_list) - nb_month) + group_list + [0]*nb_month
        return res

    def _get_validate_saleorder_per_duration(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, [])
        obj = self.pool.get('sale.order')
        today = date.today().replace(day=1)
        begin = (today + relativedelta(months=-5)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        for section in self.browse(cr, uid, ids, context=context):
            domain = [("section_id", "=", section.id), ('state', 'not in', ['draft', 'sent']), ('date_confirm', '>=', begin)]
            group_obj = obj.read_group(cr, uid, domain, ['amount_total', "date_confirm"], "date_confirm", context=context)
            group_list = [group['amount_total'] for group in group_obj]
            nb_month = group_obj and relativedelta(today, datetime.strptime(group_obj[-1]['__domain'][0][2], '%Y-%m-%d')).months or 0
            res[section.id] = [0]*(5 - len(group_list) - nb_month) + group_list + [0]*nb_month
        return res

    def _get_sent_invoice_per_duration(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, [])
        obj = self.pool.get('account.invoice.report')
        today = date.today().replace(day=1)
        begin = (today + relativedelta(months=-5)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        for section in self.browse(cr, uid, ids, context=context):
            domain = [("section_id", "=", section.id), ('state', 'not in', ['draft', 'cancel']), ('date', '>=', begin)]
            group_obj = obj.read_group(cr, uid, domain, ['price_total', "date"], "date", context=context)
            group_list = [group['price_total'] for group in group_obj]
            nb_month = group_obj and relativedelta(today, datetime.strptime(group_obj[-1]['__domain'][0][2], '%Y-%m-%d')).months or 0
            res[section.id] = [0]*(5 - len(group_list) - nb_month) + group_list + [0]*nb_month
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

        'forecast': fields.integer(string='Total forecast'),
        'target_invoice': fields.integer(string='Invoicing Target'),
        'created_quotation_per_duration': fields.function(_get_created_quotation_per_duration, string='Rate of created quotation per duration', type="string", readonly=True),
        'validate_saleorder_per_duration': fields.function(_get_validate_saleorder_per_duration, string='Rate of validate sales orders per duration', type="string", readonly=True),
        'sent_invoice_per_duration': fields.function(_get_sent_invoice_per_duration, string='Rate of sent invoices per duration', type="string", readonly=True),
    }

    def action_forecast(self, cr, uid, id, value, context=None):
        return self.write(cr, uid, [id], {'forecast': value}, context=context)

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
