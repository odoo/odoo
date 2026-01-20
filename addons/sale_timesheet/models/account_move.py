# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.fields import Domain


class AccountMove(models.Model):
    _inherit = "account.move"

    timesheet_ids = fields.One2many('account.analytic.line', 'reinvoice_id', string='Timesheets', readonly=True, copy=False, export_string_translation=False)
    timesheet_count = fields.Integer("Number of timesheets", compute='_compute_timesheet_count', compute_sudo=True, export_string_translation=False)
    timesheet_encode_uom_id = fields.Many2one('uom.uom', related='company_id.timesheet_encode_uom_id', export_string_translation=False)
    timesheet_total_duration = fields.Integer("Timesheet Total Duration",
        compute='_compute_timesheet_total_duration', compute_sudo=True,
        help="Total recorded duration, expressed in the encoding UoM, and rounded to the unit")

    @api.depends('timesheet_ids', 'company_id.timesheet_encode_uom_id')
    def _compute_timesheet_total_duration(self):
        if not self.env.user.has_group('hr_timesheet.group_hr_timesheet_user'):
            self.timesheet_total_duration = 0
            return
        group_data = self.env['account.analytic.line']._read_group([
            ('reinvoice_id', 'in', self.ids), ('project_id', '!=', False),
        ], ['reinvoice_id'], ['unit_amount:sum'])
        timesheet_unit_amount_dict = defaultdict(float)
        timesheet_unit_amount_dict.update({timesheet_invoice.id: amount for timesheet_invoice, amount in group_data})
        for invoice in self:
            total_time = invoice.company_id.project_time_mode_id._compute_quantity(
                timesheet_unit_amount_dict[invoice.id],
                invoice.timesheet_encode_uom_id,
                rounding_method='HALF-UP',
            )
            invoice.timesheet_total_duration = round(total_time)

    @api.depends('timesheet_ids')
    def _compute_timesheet_count(self):
        timesheet_data = self.env['account.analytic.line']._read_group([('reinvoice_id', 'in', self.ids)], ['reinvoice_id'], ['__count'])
        mapped_data = {timesheet_invoice.id: count for timesheet_invoice, count in timesheet_data}
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
            'view_mode': 'list,form',
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

    def action_post(self):
        result = super().action_post()
        credit_notes = self.filtered(lambda move: move.move_type == 'out_refund' and move.reversed_entry_id)
        timesheets_sudo = self.env['account.analytic.line'].sudo().search([
            ('reinvoice_id', 'in', credit_notes.reversed_entry_id.ids),
            ('so_line', 'in', credit_notes.invoice_line_ids.sale_line_ids.ids),
            ('project_id', '!=', False),
        ])
        timesheets_sudo.write({'reinvoice_id': False})
        return result

    def _domain_services_analytic_line(self):
        """To make sure we see only services analytic line that are not timesheets"""
        domain = super()._domain_services_analytic_line()

        return domain & Domain('project_id', '=', False)

    def _filter_sale_lines_to_reinvoice(self, sale_line):
        """If a project or task is created on order confirmation, we will link lines which are linked
        to timesheets."""
        return super()._filter_sale_lines_to_reinvoice(sale_line) and (
            sale_line.product_id.service_tracking == 'no'
            or (
                sale_line.product_id.service_tracking in (
                    'task_global_project',
                    'task_in_project',
                    'project_only',
                )
                and sale_line.product_id.service_type == 'timesheet'
            )
        )
