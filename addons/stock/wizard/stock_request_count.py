# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.fields import Domain


class StockRequestCount(models.TransientModel):
    _name = 'stock.request.count'
    _description = 'Stock Request an Inventory Count'

    inventory_date = fields.Date(
        'Scheduled at', required=True,
        help="Choose a date to get the inventory at that date",
        default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', string="Assign to", domain=lambda self: [('all_group_ids', 'in', self.env.ref('stock.group_stock_user').id)])
    quant_ids = fields.Many2many('stock.quant')
    show_expected_quantity = fields.Boolean(help='If the user can see the expected quantity or not', compute='_compute_show_expected_quantity', inverse='_set_show_expected_quantity')

    def _compute_show_expected_quantity(self):
        show_quantity_count = self.env['ir.config_parameter'].sudo().get_param('stock.show_expected_quantity_count', default='False') == 'True'
        for record in self:
            record.show_expected_quantity = show_quantity_count

    def _set_show_expected_quantity(self):
        for record in self:
            if record.show_expected_quantity:
                self.env['ir.config_parameter'].sudo().set_param('stock.show_expected_quantity_count', 'True')
            else:
                self.env['ir.config_parameter'].sudo().set_param('stock.show_expected_quantity_count', 'False')

    def action_request_count(self):
        for count_request in self:
            quants_to_count = count_request._get_quants_to_count()
            values = count_request._get_values_to_write()
            quants_to_count.with_context(inventory_mode=True).write(values)

    def _get_quants_to_count(self):
        self.ensure_one()
        quants_to_count = self.quant_ids
        tracked_quants = self.quant_ids.filtered(lambda q: q.product_id.tracking != 'none')
        if not self.env.user.has_group('stock.group_production_lot') or not tracked_quants:
            return quants_to_count
        # Searches sibling quants for tracked product.
        if tracked_quants:
            domain = {
                Domain('product_id', '=', quant.product_id.id) & Domain('location_id', '=', quant.location_id.id)
                for quant in tracked_quants
            }
            domain = Domain.OR(domain)
            sibling_quants = self.env['stock.quant'].search(domain)
            quants_to_count |= sibling_quants
        return quants_to_count

    def _get_values_to_write(self):
        values = {
            'inventory_date': self.inventory_date,
        }
        if self.user_id:
            values['user_id'] = self.user_id.id,
        return values
