# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round, float_is_zero


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

    @api.multi
    def invoice_validate(self):
        result = super(AccountInvoice, self).invoice_validate()
        # associate the invoice to the timesheet on validation
        for invoice in self:
            for invoice_line in invoice.invoice_line_ids.filtered(lambda line: line.product_id.type == 'service').sorted(key=lambda inv_line: (inv_line.invoice_id, inv_line.id)):
                uninvoiced_timesheet_lines = self.env['account.analytic.line'].sudo().search([
                    ('so_line', 'in', invoice_line.sale_line_ids.ids),
                    ('project_id', '!=', False),
                    ('timesheet_invoice_id', '=', False),
                    ('timesheet_invoice_type', 'in', ['billable_time', 'billable_fixed'])
                ])
                uninvoiced_timesheet_lines.write({'timesheet_invoice_id': invoice.id})
        return result
