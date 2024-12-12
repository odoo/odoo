from uuid import uuid4

from odoo import api, fields, models, tools, _, Command

class PosPreparationOrder(models.Model):
    _name = 'pos.preparation.order'
    _description = "Subset of pos order that is to be prepared; a record of pos.preparation.order will be created each time the user clicks on the `Order`"
    _inherit = ['pos.load.mixin']

    order_id = fields.Many2one('pos.order', string='Order', required=True, ondelete='cascade')
    preparation_line_ids = fields.One2many('pos.preparation.orderline', 'preparation_order_id', string="Order Lines")
    uuid = fields.Char(string='Uuid', readonly=True, default=lambda self: str(uuid4()), copy=False)
    # preparation_order_type = fields.Selection([('new', 'New'), ('cancelled', 'Cancelled'), ('note_update', 'Note Update')], string='Type', default='new')
    note = fields.Text("Note")
    printed = fields.Boolean("Printed", default=False)

    @api.model
    def _load_pos_data_domain(self, data):
        return [("order_id", "in", [order["id"] for order in data["pos.order"]])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['order_id', 'preparation_line_ids', 'note', 'uuid']


class PosPreparationOrderline(models.Model):
    _name = 'pos.preparation.orderline'
    _description = "Subset of pos orderline that is to be prepared"
    _inherit = ['pos.load.mixin']

    preparation_order_id = fields.Many2one('pos.preparation.order', string='Order', ondelete='cascade')
    pos_orderline_id = fields.Many2one('pos.order.line', string='Order Line', ondelete='cascade', required=True)
    qty = fields.Float("Quantity", required=True)
    note = fields.Text("Note")
    uuid = fields.Char(string='Uuid', readonly=True, default=lambda self: str(uuid4()), copy=False)

    @api.model
    def _load_pos_data_domain(self, data):
        return [("preparation_order_id", "in", [order["id"] for order in data["pos.preparation.order"]])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['preparation_order_id', 'pos_orderline_id', 'qty', 'note', 'uuid']
