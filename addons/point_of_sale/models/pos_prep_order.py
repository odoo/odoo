from odoo import fields, models, api
from uuid import uuid4


class PosPrepOrder(models.Model):
    _name = 'pos.prep.order'
    _description = 'Pos Preparation Order'
    _inherit = ['pos.load.mixin']

    pos_order_id = fields.Many2one('pos.order', string='Order', ondelete='cascade', index='btree_not_null')
    prep_line_ids = fields.One2many('pos.prep.line', 'prep_order_id', string='Preparation Lines')
    uuid = fields.Char(string='Uuid', readonly=True, default=lambda self: str(uuid4()), copy=False)

    @api.model
    def _compute_prep_order(self, order_id):
        order = self.env['pos.order'].browse(order_id)

        existing_prep_order = self.env['pos.prep.order'].search([('pos_order_id', '=', order.id)], limit=1)
        if not existing_prep_order:
            prep_order = self.env['pos.prep.order'].create({
                'pos_order_id': order.id,
            })
            for line in order.lines:
                parent = False
                if line.combo_parent_id:
                    parent = self.env['pos.prep.line'].search([
                        ('pos_order_line_uuid', '=', line.combo_parent_id.uuid),
                        ('prep_order_id', '=', prep_order.id)
                    ], limit=1)
                self.env['pos.prep.line'].create({
                    'attribute_value_ids': line.attribute_value_ids.ids,
                    'product_id': line.product_id.id,
                    'quantity': line.qty,
                    'prep_order_id': prep_order.id,
                    'pos_order_line_uuid': line.uuid,
                    'pos_order_line_id': line.id,
                    'combo_parent_id': parent.id if parent else False,
                })
