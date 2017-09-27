# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    timesheet_ids = fields.One2many('account.analytic.line', 'timesheet_invoice_id', string='Timesheets', readonly=True, copy=False)
    timesheet_count = fields.Integer("Number of timesheets", compute='_compute_timesheet_count')

    @api.multi
    @api.depends('timesheet_ids')
    def _compute_timesheet_count(self):
        timesheet_data = self.env['account.analytic.line'].read_group([('timesheet_invoice_id', 'in', self.ids)], ['timesheet_invoice_id'], ['timesheet_invoice_id'])
        mapped_data = dict([(t['timesheet_invoice_id'][0], t['timesheet_invoice_id_count']) for t in timesheet_data])
        for invoice in self:
            invoice.timesheet_count = mapped_data.get(invoice.id, 0)

    def action_view_timesheet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Timesheets'),
            'domain': [('project_id', '!=', False)],
            'res_model': 'account.analytic.line',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'help': _("""
                <p class="oe_view_nocontent_create">
                    Click to record timesheets.
                </p><p>
                    You can register and track your workings hours by project every
                    day. Every time spent on a project will become a cost and can be re-invoiced to
                    customers if required.
                </p>
            """),
            'limit': 80,
            'context': {
                'default_project_id': self.id,
                'search_default_project_id': [self.id]
            }
        }

    @api.multi
    def invoice_validate(self):
        result = super(AccountInvoice, self).invoice_validate()
        self._compute_timesheet_revenue()
        return result

    def _compute_timesheet_revenue(self):
        for invoice in self:
            for invoice_line in invoice.invoice_line_ids.filtered(lambda line: line.product_id.type == 'service').sorted(key=lambda inv_line: (inv_line.invoice_id, inv_line.id)):
                uninvoiced_timesheet_lines = self.env['account.analytic.line'].sudo().search([
                    ('so_line', 'in', invoice_line.sale_line_ids.ids),
                    ('project_id', '!=', False),
                    ('timesheet_invoice_id', '=', False),
                    ('timesheet_invoice_type', 'in', ['billable_time', 'billable_fixed'])
                ])

                # NOTE JEM : changing quantity (or unit price) of invoice line does not impact the revenue calculation. (FP specs)
                if uninvoiced_timesheet_lines:
                    # delivered : update revenue with the prorata of number of hours on the timesheet line
                    if invoice_line.product_id.invoice_policy == 'delivery':
                        invoiced_price_per_hour = invoice_line.currency_id.round(invoice_line.price_subtotal / float(sum(uninvoiced_timesheet_lines.mapped('unit_amount'))))
                        # invoicing analytic lines of different currency
                        total_revenue_per_currency = dict.fromkeys(uninvoiced_timesheet_lines.mapped('company_currency_id').ids, 0.0)
                        for index, timesheet_line in enumerate(uninvoiced_timesheet_lines.sorted(key=lambda ts: (ts.date, ts.id))):
                            if index+1 != len(uninvoiced_timesheet_lines):
                                line_revenue = invoice_line.currency_id.compute(invoiced_price_per_hour, timesheet_line.company_currency_id) * timesheet_line.unit_amount
                                total_revenue_per_currency[timesheet_line.company_currency_id.id] += line_revenue
                            else:  # last line: add the difference to avoid rounding problem
                                total_revenue = sum([self.env['res.currency'].browse(currency_id).compute(amount, timesheet_line.company_currency_id) for currency_id, amount in total_revenue_per_currency.items()])
                                line_revenue = invoice_line.currency_id.compute(invoice_line.price_subtotal, timesheet_line.company_currency_id) - total_revenue
                            timesheet_line.write({
                                'timesheet_invoice_id': invoice.id,
                                'timesheet_revenue': timesheet_line.company_currency_id.round(line_revenue),
                            })

                    # ordered : update revenue with the prorata of theorical revenue
                    elif invoice_line.product_id.invoice_policy == 'order':
                        zero_timesheet_revenue = uninvoiced_timesheet_lines.filtered(lambda line: line.timesheet_revenue == 0.0)
                        no_zero_timesheet_revenue = uninvoiced_timesheet_lines.filtered(lambda line: line.timesheet_revenue != 0.0)

                        # timesheet with zero theorical revenue keep the same revenue, but become invoiced (invoice_id set)
                        zero_timesheet_revenue.write({'timesheet_invoice_id': invoice.id})

                        # invoicing analytic lines of different currency
                        total_revenue_per_currency = dict.fromkeys(no_zero_timesheet_revenue.mapped('company_currency_id').ids, 0.0)

                        for index, timesheet_line in enumerate(no_zero_timesheet_revenue.sorted(key=lambda ts: (ts.date, ts.id))):
                            if index+1 != len(no_zero_timesheet_revenue):
                                price_subtotal_inv = invoice_line.currency_id.compute(invoice_line.price_subtotal, timesheet_line.company_currency_id)
                                price_subtotal_sol = timesheet_line.so_line.currency_id.compute(timesheet_line.so_line.price_subtotal, timesheet_line.company_currency_id)
                                line_revenue = timesheet_line.timesheet_revenue * price_subtotal_inv / price_subtotal_sol
                                total_revenue_per_currency[timesheet_line.company_currency_id.id] += line_revenue
                            else:  # last line: add the difference to avoid rounding problem
                                last_price_subtotal_inv = invoice_line.currency_id.compute(invoice_line.price_subtotal, timesheet_line.company_currency_id)
                                total_revenue = sum([self.env['res.currency'].browse(currency_id).compute(amount, timesheet_line.company_currency_id) for currency_id, amount in total_revenue_per_currency.items()])
                                line_revenue = last_price_subtotal_inv - total_revenue

                            timesheet_line.write({
                                'timesheet_invoice_id': invoice.id,
                                'timesheet_revenue': timesheet_line.company_currency_id.round(line_revenue),
                            })
