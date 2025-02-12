from odoo import api, fields, models, tools, _, Command

class PosPreparationOrder(models.Model):
    _name = 'pos.preparation.order'
    _description = "Subset of pos order that is to be prepared"

    order_id = fields.Many2one('pos.order', string='Order', required=True, ondelete='cascade')
    line_ids = fields.One2many('pos.preparation.orderline', 'order_id', string="Order Lines")
    customer_note = fields.Text("General Customer Note", help="")
    internal_note = fields.Text("General Note", help="")

    @api.model
    def _load_pos_data_domain(self, data):
        return [("order_id", "in", [order["id"] for order in data["pos.order"]])]

    @api.model
    def _load_pos_data_fields(self):
        return ['order_id', 'line_ids', 'customer_note', 'internal_note']

    @api.model
    def _load_pos_data_models(self, config_id):
        return super()._load_pos_data_models(config_id) + ['pos.preparation.order']

class PosPreparationOrderline(models.Model):
    _name = 'pos.preparation.orderline'
    _description = "Subset of pos orderline that is to be prepared"

    order_id = fields.Many2one('pos.preparation.order', string='Order', required=True, ondelete='cascade')
    pos_orderline_id = fields.Many2one('pos.order.line', string='Order Line', required=True, ondelete='cascade')
    qty = fields.Float("Quantity", required=True)
    note = fields.Text("Note")

    @api.model
    def _load_pos_data_domain(self, data):
        return [("order_id", "in", [order["id"] for order in data["pos.preparation.order"]])]

    @api.model
    def _load_pos_data_fields(self):
        return ['order_id', 'pos_orderline_id', 'qty', 'note']

    @api.model
    def _load_pos_data_models(self, config_id):
        return super()._load_pos_data_models(config_id) + ['pos.preparation.orderline']
