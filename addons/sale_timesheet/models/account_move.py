# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
from collections import defaultdict

from odoo import api, fields, models
from odoo.osv import expression


class AccountMove(models.Model):
    _inherit = "account.move"

    timesheet_ids = fields.One2many('account.analytic.line', 'timesheet_invoice_id', string='Timesheets', readonly=True, copy=False, export_string_translation=False)
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
            ('timesheet_invoice_id', 'in', self.ids)
        ], ['timesheet_invoice_id'], ['unit_amount:sum'])
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
        timesheet_data = self.env['account.analytic.line']._read_group([('timesheet_invoice_id', 'in', self.ids)], ['timesheet_invoice_id'], ['__count'])
        mapped_data = {timesheet_invoice.id: count for timesheet_invoice, count in timesheet_data}
        for invoice in self:
            invoice.timesheet_count = mapped_data.get(invoice.id, 0)

    def _has_timesheet_portal(self):
        Timesheet = self.env['account.analytic.line']
        initial_domain = Timesheet._timesheet_get_portal_domain()
        domain = expression.AND([initial_domain, self.env['account.analytic.line']._timesheet_get_sale_domain(self.line_ids.sale_line_ids, self)])
        return Timesheet.sudo().search(domain, limit=1)

    def action_view_timesheet(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('sale_timesheet.action_timesheet_from_invoice')
        context = ast.literal_eval(action.get('context', '{}'))
        context['default_is_so_line_edited'] = True

        default_so_line = next((
            sale_line for sale_line in self.line_ids.sale_line_ids
            if sale_line.is_service and sale_line.product_id.service_policy != 'delivered_timesheet'
        ), False)
        if default_so_line:
            context.update({
                'default_so_line': default_so_line.id,
                'default_timesheet_invoice_id': self.id,
                'default_task_id': default_so_line.task_id.id,
                'default_project_id': default_so_line.project_id.id or default_so_line.task_id.project_id.id,
            })
        action['context'] = context

        return action

    def _link_timesheets_to_invoice(self, start_date=None, end_date=None, service_policies=['delivered_timesheet']):
        """ Search timesheets from given period and link this timesheets to the invoice

            When we create an invoice from a sale order, we need to
            link the timesheets in this sale order to the invoice.
            Then, we can know which timesheets are invoiced in the sale order.
            :param start_date: the start date of the period
            :param end_date: the end date of the period
            :param service_policies: the service policies of the sol products to consider
        """
        for line in self.filtered(lambda i: i.move_type in ['out_invoice', 'out_refund'] and i.state == 'draft').invoice_line_ids:
            sale_line_delivery = line.sale_line_ids.filtered(lambda sol: sol.product_id.service_policy in service_policies)
            if sale_line_delivery:
                domain = line._timesheet_domain_get_invoiced_lines(sale_line_delivery)
                if start_date:
                    domain = expression.AND([domain, [('date', '>=', start_date)]])
                if sale_line_delivery.product_id.service_policy == 'delivered_manual':
                    end_date = line.move_id.invoice_date or fields.Date.today()
                if end_date:
                    domain = expression.AND([domain, [('date', '<=', end_date)]])
                timesheets = self.env['account.analytic.line'].sudo().search(domain)
                timesheets.write({'timesheet_invoice_id': line.move_id.id})

    def _unlink_timesheets_from_invoice(self, service_policies):
        for move in self:
            if move.move_type in ['out_invoice', 'out_refund'] and move.state == 'posted':
                timesheets = move.timesheet_ids.filtered(lambda t: t.so_line.product_id.service_policy in service_policies)
                timesheets.timesheet_invoice_id = False

    def _post(self, soft=True):
        self._link_timesheets_to_invoice(service_policies=['delivered_milestones', 'delivered_manual'])
        return super()._post(soft)

    def button_draft(self):
        self._unlink_timesheets_from_invoice(['ordered_prepaid', 'delivered_milestones', 'delivered_manual'])
        return super().button_draft()

    def _reverse_moves(self, default_values_list=None, cancel=False):
        reverse_moves = super()._reverse_moves(default_values_list, cancel)
        (self + reverse_moves)._unlink_timesheets_from_invoice(['ordered_prepaid', 'delivered_milestones', 'delivered_manual'])
        return reverse_moves
