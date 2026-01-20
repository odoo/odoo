# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, models
from odoo.fields import Domain


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def _analytic_line_domain_get_invoiced_lines(self, sale_line):
        domain = super()._analytic_line_domain_get_invoiced_lines(sale_line)

        start_date = self.env.context.get('timesheet_start_date', False)
        end_date = self.env.context.get('timesheet_end_date', False)

        if not start_date or not end_date:
            start_date, end_date = self._get_range_dates(sale_line.order_id)

        if start_date:
            domain &= Domain('date', '>=', start_date)
        if end_date:
            domain &= Domain('date', '<=', end_date)

        return domain

    def _get_range_dates(self, order):
        # A method that can be overridden
        # to set the start and end dates according to order values
        return None, None

    def unlink(self):
        move_line_read_group = self.env['account.move.line'].search_read([
            ('move_id.move_type', '=', 'out_invoice'),
            ('move_id.state', '=', 'draft'),
            ('sale_line_ids.product_id.invoice_policy', '=', 'delivery'),
            ('sale_line_ids.product_id.service_type', '=', 'timesheet'),
            ('id', 'in', self.ids)],
            ['move_id', 'sale_line_ids'])

        sale_line_ids_per_move = defaultdict(lambda: self.env['sale.order.line'])
        for move_line in move_line_read_group:
            sale_line_ids_per_move[move_line['move_id'][0]] += self.env['sale.order.line'].browse(move_line['sale_line_ids'])

        timesheet_read_group = self.sudo().env['account.analytic.line']._read_group([
            ('reinvoice_id.move_type', '=', 'out_invoice'),
            ('reinvoice_id.state', '=', 'draft'),
            ('reinvoice_id', 'in', self.move_id.ids)],
            ['reinvoice_id', 'so_line'],
            ['id:array_agg'])

        timesheet_ids = []
        for timesheet_invoice, so_line, ids in timesheet_read_group:
            if so_line.id in sale_line_ids_per_move[timesheet_invoice.id].ids:
                timesheet_ids += ids

        self.sudo().env['account.analytic.line'].browse(timesheet_ids).write({'reinvoice_id': False})
        return super().unlink()
