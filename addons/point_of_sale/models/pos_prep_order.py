from odoo import fields, models, api
from uuid import uuid4


class PosPrepOrder(models.Model):
    _name = 'pos.prep.order'
    _description = 'Pos Preparation Order'
    _inherit = ['pos.load.mixin']

    prep_order_group_id = fields.Many2one('pos.prep.order.group', string='Preparation Order Group', index='btree_not_null')
    pos_order_id = fields.Many2one('pos.order', string='Order', ondelete='cascade', index='btree_not_null')
    prep_line_ids = fields.One2many('pos.prep.line', 'prep_order_id', string='Preparation Lines')
    uuid = fields.Char(string='Uuid', readonly=True, default=lambda self: str(uuid4()), copy=False)

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('pos_order_id', 'in', [order['id'] for order in data['pos.order']])]
