# -*- coding: utf-8 -*-

import calendar
from datetime import date
from dateutil import relativedelta
import json

from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.float_utils import float_repr

class crm_team(osv.Model):
    _inherit = 'crm.team'

    def _get_sales_to_invoice_amount(self, cr, uid, ids, field_name, arg, context=None):
        obj = self.pool['sale.order']

        res = dict.fromkeys(ids, 0)
        domain = [
            ('team_id', 'in', ids),
            ('state', '=', 'manual'),
        ]
        amounts = obj.read_group(cr, uid, domain, ['amount_total', 'team_id'], ['team_id'], context=context)
        for rec in amounts:
            res[rec['team_id'][0]] = rec['amount_total']
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
        'sales_to_invoice_amount': fields.function(_get_sales_to_invoice_amount,
            type='integer', readonly=True,
            string='Amount of sales to invoice'),
    }

    _defaults = {
        'use_quotations': True,
    }

    def action_forecast(self, cr, uid, id, value, context=None):
        return self.write(cr, uid, [id], {'invoiced_forecast': round(float(value))}, context=context)
