from odoo import fields, models, api
from uuid import uuid4


class PosPrepLine(models.Model):
    _name = 'pos.prep.line'
    _description = 'Pos Preparation Line'
    _inherit = ['pos.load.mixin']

    prep_order_id = fields.Many2one('pos.prep.order', string='Preparation Order', ondelete='cascade', index='btree_not_null')
    pos_order_line_id = fields.Many2one('pos.order.line', string="Original pos order line", index='btree_not_null')
    quantity = fields.Float('Quantity', required=True)
    uuid = fields.Char(string='Uuid', readonly=True, default=lambda self: str(uuid4()), copy=False)
    cancelled = fields.Float("Quantity of cancelled product")
    combo_line_ids = fields.One2many('pos.prep.line', 'combo_parent_id')

    # PoS orderline computed fields, we cannot use related fields because the pos line can be deleted
    combo_parent_id = fields.Many2one('pos.prep.line', compute="_compute_combo_fields", store=True, index='btree_not_null')
    product_id = fields.Many2one('product.product', compute="_compute_combo_fields", store=True)
    attribute_value_ids = fields.Many2many('product.template.attribute.value', compute="_compute_combo_fields", store=True)

    # Prep orderlines group for splitting
    child_prep_line_ids = fields.One2many('pos.prep.line', 'parent_prep_line_id')
    parent_prep_line_id = fields.Many2one('pos.prep.line', string="original splitted prep line", index='btree_not_null')

    @api.depends('pos_order_line_id', 'pos_order_line_id.combo_line_ids', 'pos_order_line_id.combo_parent_id')
    def _compute_combo_fields(self):
        for line in self:
            pos_line = line.pos_order_line_id

            if pos_line.exists():
                line.attribute_value_ids = pos_line.attribute_value_ids

            if pos_line.product_id:
                line.product_id = pos_line.product_id

            if pos_line.combo_parent_id:
                line.combo_parent_id = pos_line.combo_parent_id.prep_line_ids

            if pos_line.combo_line_ids:
                line.combo_line_ids = pos_line.combo_line_ids.mapped('prep_line_ids')

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('prep_order_id', 'in', [order['id'] for order in data['pos.prep.order']])]
