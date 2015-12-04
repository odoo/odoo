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

    def _get_monthly_invoiced(self, cr, uid, ids, field_name, arg, context=None):
        obj_inv = self.pool['account.invoice']
        res = dict.fromkeys(ids, 0)

        # Cannot use read_group because amount_untaxed_signed is an unstored computed field
        for team in ids:
            domain = [
                ('state', 'in', ['open', 'paid']),
                ('team_id', '=', team),
                ('date', '<=', date.today()),
                ('date', '>=', date.today().replace(day=1))
            ]
            invoices = obj_inv.search_read(cr, uid, domain, ['amount_untaxed_signed'], context=context)
            res[team] = sum([inv['amount_untaxed_signed'] for inv in invoices])
        return res

    _columns = {
        'use_quotations': fields.boolean('Quotations', help="Check this box to manage quotations in this sales team."),
        'use_invoices': fields.boolean('Invoices', help="Check this box to manage invoices in this sales team."),
        'invoiced': fields.function(_get_monthly_invoiced, type='integer', readonly=True, string='Invoiced This Month',
            help="Invoice revenue for the current month. This is the amount the sales "
                    "team has invoiced this month. It is used to compute the progression ratio "
                    "of the current and target revenue on the kanban view."),
        'invoiced_target': fields.integer(string='Invoice Target',
            help="Target of invoice revenue for the current month. This is the amount the sales "
                    "team estimates to be able to invoice this month."),
        'sales_to_invoice_amount': fields.function(_get_sales_to_invoice_amount,
            type='integer', readonly=True,
            string='Amount of sales to invoice'),
        'currency_id': fields.related('company_id', 'currency_id', type="many2one", relation="res.currency", string="Currency", readonly=True, required=True),
    }

    _defaults = {
        'use_quotations': True,
    }

    def update_invoiced_target(self, cr, uid, id, value, context=None):
        return self.write(cr, uid, [id], {'invoiced_target': round(float(value or 0))}, context=context)
