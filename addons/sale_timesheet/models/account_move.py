# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round, float_is_zero


class AccountMove(models.Model):
    _inherit = "account.move"

    timesheet_ids = fields.One2many('account.analytic.line', 'timesheet_invoice_id', string='Timesheets', readonly=True, copy=False)
    timesheet_count = fields.Integer("Number of timesheets", compute='_compute_timesheet_count')

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
            'help': _("""
                <p class="o_view_nocontent_smiling_face">
                    Record timesheets
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


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        # Link the timesheet from the SO lines to the corresponding draft invoice.
        # NOTE: Only the timesheets linked to an Sale Line with a product invoiced on delivered quantity
        # are concerned, since in ordered quantity, the timesheet quantity is not invoiced, but is simply
        # to compute the delivered one (for reporting).
        lines = super(AccountMoveLine, self).create(vals_list)
        lines_to_process = lines.filtered(lambda line: line.move_id.type == 'out_invoice'
                                                       and line.move_id.state == 'draft')
        for line in lines_to_process:
            sale_line_delivery = line.sale_line_ids.filtered(lambda sol: sol.product_id.invoice_policy == 'delivery' and sol.product_id.service_type == 'timesheet')
            if sale_line_delivery:
                domain = self._timesheet_domain_get_invoiced_lines(sale_line_delivery)
                timesheets = self.env['account.analytic.line'].search(domain)
                timesheets.write({
                    'timesheet_invoice_id': line.move_id.id,
                })
        return lines

    @api.model
    def _timesheet_domain_get_invoiced_lines(self, sale_line_delivery):
        """ Get the domain for the timesheet to link to the created invoice
            :param sale_line_delivery: recordset of sale.order.line to invoice
            :return a normalized domain
        """
        return [
            '&',
            ('so_line', 'in', sale_line_delivery.ids),
            '&',
            ('timesheet_invoice_id', '=', False),
            ('project_id', '!=', False)
        ]
