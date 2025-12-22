# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def _timesheet_domain_get_invoiced_lines(self, sale_line_delivery):
        """ Get the domain for the timesheet to link to the created invoice
            :param sale_line_delivery: recordset of sale.order.line to invoice
            :return a normalized domain
        """
        return [
            ('so_line', 'in', sale_line_delivery.ids),
            ('project_id', '!=', False),
            '|', '|',
                ('timesheet_invoice_id', '=', False),
                '&',
                    ('timesheet_invoice_id.state', '=', 'cancel'),
                    ('timesheet_invoice_id.payment_state', '!=', 'invoicing_legacy'),
                ('timesheet_invoice_id.payment_state', '=', 'reversed')
        ]

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
            ('timesheet_invoice_id.move_type', '=', 'out_invoice'),
            ('timesheet_invoice_id.state', '=', 'draft'),
            ('timesheet_invoice_id', 'in', self.move_id.ids)],
            ['timesheet_invoice_id', 'so_line'],
            ['id:array_agg'])

        timesheet_ids = []
        for timesheet_invoice, so_line, ids in timesheet_read_group:
            if so_line.id in sale_line_ids_per_move[timesheet_invoice.id].ids:
                timesheet_ids += ids

        self.sudo().env['account.analytic.line'].browse(timesheet_ids).write({'timesheet_invoice_id': False})
        return super().unlink()
