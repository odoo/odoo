# -*- coding: utf-8 -*-

import calendar
from datetime import date
from dateutil import relativedelta
import json

from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.float_utils import float_repr

class crm_case_section(osv.osv):
    _inherit = 'crm.case.section'

    def _get_sale_orders_data(self, cr, uid, ids, field_name, arg, context=None):
        obj = self.pool['sale.order']
        month_begin = date.today().replace(day=1)
        date_begin = (month_begin - relativedelta.relativedelta(months=self._period_number - 1)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        date_end = month_begin.replace(day=calendar.monthrange(month_begin.year, month_begin.month)[1]).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)

        res = {}
        for id in ids:
            res[id] = {}
            created_domain = [('section_id', '=', id), ('state', '=', 'draft'), ('date_order', '>=', date_begin), ('date_order', '<=', date_end)]
            validated_domain = [('section_id', '=', id), ('state', 'not in', ['draft', 'sent', 'cancel']), ('date_order', '>=', date_begin), ('date_order', '<=', date_end)]
            res[id]['monthly_quoted'] = json.dumps(self.__get_bar_values(cr, uid, obj, created_domain, ['amount_total', 'date_order'], 'amount_total', 'date_order', context=context))
            res[id]['monthly_confirmed'] = json.dumps(self.__get_bar_values(cr, uid, obj, validated_domain, ['amount_total', 'date_order'], 'amount_total', 'date_order', context=context))

        return res

    def _get_invoices_data(self, cr, uid, ids, field_name, arg, context=None):
        obj = self.pool['account.invoice.report']
        month_begin = date.today().replace(day=1)
        date_begin = (month_begin - relativedelta.relativedelta(months=self._period_number - 1)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        date_end = month_begin.replace(day=calendar.monthrange(month_begin.year, month_begin.month)[1]).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)

        res = {}
        for id in ids:
            created_domain = [('section_id', '=', id), ('state', 'not in', ['draft', 'cancel']), ('date', '>=', date_begin), ('date', '<=', date_end)]
            values = self.__get_bar_values(cr, uid, obj, created_domain, ['price_total', 'date'], 'price_total', 'date', context=context)
            for value in values:
                value['value'] = float_repr(value.get('value', 0), precision_digits=self.pool['decimal.precision'].precision_get(cr, uid, 'Account'))
            res[id] = json.dumps(values)
        return res

    _columns = {
        'use_quotations': fields.boolean('Quotations', help="Check this box to manage quotations in this sales team."),
        'invoiced_forecast': fields.integer(string='Invoice Forecast',
            help="Forecast of the invoice revenue for the current month. This is the amount the sales \n"
                    "team should invoice this month. It is used to compute the progression ratio \n"
                    " of the current and forecast revenue on the kanban view."),
        'invoiced_target': fields.integer(string='Invoice Target',
            help="Target of invoice revenue for the current month. This is the amount the sales \n"
                    "team estimates to be able to invoice this month."),
        'monthly_quoted': fields.function(_get_sale_orders_data,
            type='char', readonly=True, multi='_get_sale_orders_data',
            string='Rate of created quotation per duration'),
        'monthly_confirmed': fields.function(_get_sale_orders_data,
            type='char', readonly=True, multi='_get_sale_orders_data',
            string='Rate of validate sales orders per duration'),
        'monthly_invoiced': fields.function(_get_invoices_data,
            type='char', readonly=True,
            string='Rate of sent invoices per duration'),
    }

    _defaults = {
        'use_quotations': True,
    }

    def action_forecast(self, cr, uid, id, value, context=None):
        return self.write(cr, uid, [id], {'invoiced_forecast': round(float(value))}, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
