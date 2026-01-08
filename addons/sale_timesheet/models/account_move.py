# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models
from odoo.fields import Domain


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
        domain = Domain.AND([initial_domain, self.env['account.analytic.line']._timesheet_get_sale_domain(self.invoice_line_ids.sale_line_ids, self)])
        return Timesheet.sudo().search(domain, limit=1)

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
            if not sale_line_delivery:
                continue
            domain = Domain(line._timesheet_domain_get_invoiced_lines(sale_line_delivery))
            timesheets_per_domain = dict()
            for sale_line in sale_line_delivery:
                sale_line_domain = domain
                if not start_date and not end_date:
                    start_date, end_date = self._get_range_dates(sale_line.order_id)
                if sale_line.product_id.service_policy == 'delivered_manual':
                    end_date = line.move_id.invoice_date or fields.Date.today()
                if start_date:
                    sale_line_domain &= Domain('date', '>=', start_date)
                if end_date:
                    sale_line_domain &= Domain('date', '<=', end_date)
                repr_domain = repr(sale_line_domain)  # Normalize the domain to make it hashable
                if repr_domain not in timesheets_per_domain:
                    timesheets_per_domain[repr_domain] = self.env['account.analytic.line'].sudo().search(sale_line_domain)
                timesheets = timesheets_per_domain[repr_domain]
                timesheets.write({'timesheet_invoice_id': line.move_id.id})

    def _get_range_dates(self, order):
        # A method that can be overridden
        # to set the start and end dates according to order values
        return None, None

    def action_post(self):
        result = super().action_post()
        credit_notes = self.filtered(lambda move: move.move_type == 'out_refund' and move.reversed_entry_id)
        timesheets_sudo = self.env['account.analytic.line'].sudo().search([
            ('timesheet_invoice_id', 'in', credit_notes.reversed_entry_id.ids),
            ('so_line', 'in', credit_notes.invoice_line_ids.sale_line_ids.ids),
            ('project_id', '!=', False),
        ])
        timesheets_sudo.write({'timesheet_invoice_id': False})
        return result

    def _unlink_timesheets_from_invoice(self, service_policies):
        for move in self:
            if move.move_type in ['out_invoice', 'out_refund'] and move.state == 'posted':
                timesheets = move.timesheet_ids.filtered(lambda t: t.service_policy in service_policies)
                timesheets.timesheet_invoice_id = False

    def _post(self, soft=True):
        self._link_timesheets_to_invoice(service_policies=['delivered_milestones', 'delivered_manual'])
        return super()._post(soft)

    def button_draft(self):
        self._unlink_timesheets_from_invoice(['ordered_prepaid', 'delivered_milestones', 'delivered_manual'])
        return super().button_draft()

    def _reverse_moves(self, default_values_list=None, cancel=False):
        reverse_moves = super()._reverse_moves(default_values_list, cancel)
        (self | reverse_moves)._unlink_timesheets_from_invoice(['ordered_prepaid', 'delivered_milestones', 'delivered_manual'])
        return reverse_moves
