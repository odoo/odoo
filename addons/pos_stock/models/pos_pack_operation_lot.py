from odoo import api, fields, models


class PosPackOperationLot(models.Model):
    _name = 'pos.pack.operation.lot'
    _description = "Specify product lot/serial number in pos order line"
    _rec_name = "lot_name"
    _inherit = ['pos.load.mixin']

    pos_order_line_id = fields.Many2one('pos.order.line', index='btree_not_null')
    order_id = fields.Many2one('pos.order', related="pos_order_line_id.order_id", readonly=False)
    lot_name = fields.Char('Lot Name')
    product_id = fields.Many2one('product.product', related='pos_order_line_id.product_id', readonly=False)

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('pos_order_line_id', 'in', [line['id'] for line in data['pos.order.line']])]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['lot_name', 'pos_order_line_id', 'write_date']
