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

from datetime import date
from dateutil import relativedelta

from openerp import tools
from openerp.osv import osv, fields


class sale_order(osv.osv):
    _inherit = 'sale.order'
    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
        'categ_ids': fields.many2many('crm.case.categ', 'sale_order_category_rel', 'order_id', 'category_id', 'Categories', \
            domain="['|',('section_id','=',section_id),('section_id','=',False), ('object_id.model', '=', 'crm.lead')]")
    }

    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        invoice_vals = super(sale_order, self)._prepare_invoice(cr, uid, order, lines, context=context)
        if order.section_id and order.section_id.id:
            invoice_vals['section_id'] = order.section_id.id
        return invoice_vals


class crm_case_section(osv.osv):
    _inherit = 'crm.case.section'

    def _get_sale_orders_data(self, cr, uid, ids, field_name, arg, context=None):
        obj = self.pool.get('sale.order')
        res = dict.fromkeys(ids, False)
        month_begin = date.today().replace(day=1)
        groupby_begin = (month_begin + relativedelta.relativedelta(months=-4)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        for id in ids:
            res[id] = dict()
            created_domain = [('section_id', '=', id), ('state', 'in', ['draft', 'sent']), ('date_order', '>=', groupby_begin)]
            res[id]['monthly_quoted'] = self.__get_bar_values(cr, uid, obj, created_domain, ['amount_total', 'date_order', 'pricelist_id'], 'amount_total', ['date_order', 'pricelist_id'], context=context)
            validated_domain = [('section_id', '=', id), ('state', 'not in', ['draft', 'sent']), ('date_confirm', '>=', groupby_begin)]
            res[id]['monthly_confirmed'] = self.__get_bar_values(cr, uid, obj, validated_domain, ['amount_total', 'date_confirm', 'pricelist_id'], 'amount_total', ['date_confirm', 'pricelist_id'], context=context)
        return res

    def _get_invoices_data(self, cr, uid, ids, field_name, arg, context=None):
        obj = self.pool.get('account.invoice.report')
        res = dict.fromkeys(ids, False)
        month_begin = date.today().replace(day=1)
        groupby_begin = (month_begin + relativedelta.relativedelta(months=-4)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        for id in ids:
            created_domain = [('section_id', '=', id), ('state', 'not in', ['draft', 'cancel']), ('date', '>=', groupby_begin)]
            res[id] = self.__get_bar_values(cr, uid, obj, created_domain, ['price_total', 'date', 'currency_id'], 'price_total', ['date', 'currency_id'], context=context)
        return res

    def _compute_amounts_in_user_currency(self, cr, uid, ids, field_names, args, context=None):
        """Compute the amounts in the currency of the user """
        res = {}
        currency_obj = self.pool.get('res.currency')
        user_currency_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id.id
        for item in self.browse(cr, uid, ids, context=context):
            base_currency_id = item.user_id.company_id.currency_id.id if item.user_id else item.create_uid.company_id.currency_id.id
            res[item.id] = {
                'user_currency_invoiced_forecast': currency_obj.compute(cr, uid, base_currency_id, user_currency_id, item.invoiced_forecast, context=context),
                'user_currency_invoiced_target': currency_obj.compute(cr, uid, base_currency_id, user_currency_id, item.invoiced_target, context=context),
            }
        return res

    def _set_forecast_target(self, cr, uid, team_id, name, value, arg, context=None):
        user_currency_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id.id
        team = self.browse(cr, uid, team_id, context=context)
        base_currency_id = team.user_id.company_id.currency_id.id if team.user_id else team.create_uid.company_id.currency_id.id
        amount  = self.pool.get('res.currency').compute(cr, uid, user_currency_id, base_currency_id, value, context=context)
        self.write(cr, uid, [team_id], {name.strip("user_currency"): amount}, context=context)
        return True

    _columns = {
        'invoiced_forecast': fields.integer("Invoice Forecast"),
        'user_currency_invoiced_forecast': fields.function(_compute_amounts_in_user_currency, fnct_inv=_set_forecast_target, string='Invoice Forecast',type='integer', multi="_compute_amounts",
            help="Forecast of the invoice revenue for the current month. This is the amount the sales \n"
                    "team should invoice this month. It is used to compute the progression ratio \n"
                    " of the current and forecast revenue on the kanban view."),
        'invoiced_target': fields.integer("Invoice Target"),
        'user_currency_invoiced_target': fields.function(_compute_amounts_in_user_currency, fnct_inv=_set_forecast_target, string='Invoice Target',type='integer', multi="_compute_amounts",
            help="Target of invoice revenue for the current month. This is the amount the sales \n"
                    "team estimates to be able to invoice this month."),
        'monthly_quoted': fields.function(_get_sale_orders_data,
            type='string', readonly=True, multi='_get_sale_orders_data',
            string='Rate of created quotation per duration'),
        'monthly_confirmed': fields.function(_get_sale_orders_data,
            type='string', readonly=True, multi='_get_sale_orders_data',
            string='Rate of validate sales orders per duration'),
        'monthly_invoiced': fields.function(_get_invoices_data,
            type='string', readonly=True,
            string='Rate of sent invoices per duration'),
        'create_uid': fields.many2one('res.users', 'Create User'),
    }

    def action_forecast(self, cr, uid, id, value, context=None):
        return self.write(cr, uid, [id], {'user_currency_invoiced_forecast': round(float(value))}, context=context)

class res_users(osv.Model):
    _inherit = 'res.users'
    _columns = {
        'default_section_id': fields.many2one('crm.case.section', 'Default Sales Team'),
    }

    def __init__(self, pool, cr):
        init_res = super(res_users, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        self.SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        self.SELF_WRITEABLE_FIELDS.extend(['default_section_id'])
        return init_res


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
