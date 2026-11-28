from uuid import uuid4
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
    expiration_date = fields.Datetime('Expiration Date', compute='_compute_expiration_date')
    uuid = fields.Char(string='Uuid', readonly=True, default=lambda self: str(uuid4()), copy=False)

    _unique_uuid = models.Constraint('unique (uuid)', 'A pack operation lot with this uuid already exists')

    @api.depends('lot_name', 'product_id', 'order_id.company_id')
    def _compute_expiration_date(self):
        if 'expiration_date' not in self.env['stock.lot']._fields:
            self.expiration_date = False
            return

        records = self.filtered(lambda r: r.lot_name and r.product_id)
        (self - records).expiration_date = False
        if not records:
            return

        lots = self.env['stock.lot'].sudo().search([
            ('name', 'in', records.mapped('lot_name')),
            ('product_id', 'in', records.product_id.ids),
        ])
        lot_by_key = {(lot.name, lot.product_id.id, lot.company_id.id): lot for lot in lots}

        for record in records:
            company_id = record.order_id.company_id.id or self.env.company.id
            stock_lot = (
                lot_by_key.get((record.lot_name, record.product_id.id, company_id))
                or lot_by_key.get((record.lot_name, record.product_id.id, False))
            )
            record.expiration_date = stock_lot.expiration_date if stock_lot else False

    @api.model
    def _load_pos_data_domain(self, data):
        return [('pos_order_line_id', 'in', data['pos.order.line'].ids)]

    @api.model
    def _load_pos_data_dependencies(self):
        return ['pos.order.line']

    @api.model
    def _load_pos_data_fields(self, config):
        return ['lot_name', 'pos_order_line_id', 'expiration_date', 'write_date', 'uuid']
