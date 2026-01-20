# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

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
            ('reinvoice_move_id.move_type', '=', 'out_invoice'),
            ('reinvoice_move_id.state', '=', 'draft'),
            ('reinvoice_move_id', 'in', self.move_id.ids)],
            ['reinvoice_move_id', 'so_line'],
            ['id:array_agg'])

        timesheet_ids = []
        for timesheet_invoice, so_line, ids in timesheet_read_group:
            if so_line.id in sale_line_ids_per_move[timesheet_invoice.id].ids:
                timesheet_ids += ids

        self.sudo().env['account.analytic.line'].browse(timesheet_ids).write({'reinvoice_move_id': False})
        return super().unlink()
