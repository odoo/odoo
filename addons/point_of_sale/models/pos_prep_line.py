from odoo import fields, models, api
from uuid import uuid4


class PosPrepLine(models.Model):
    _name = 'pos.prep.line'
    _description = 'Pos Preparation Line'
    _inherit = ['pos.load.mixin']

    prep_order_id = fields.Many2one('pos.prep.order', string='Preparation Order', ondelete='cascade', index='btree_not_null')
    pos_order_line_id = fields.Many2one('pos.order.line', string="Original pos order line")
    quantity = fields.Float('Quantity', required=True)
    uuid = fields.Char(string='Uuid', readonly=True, default=lambda self: str(uuid4()), copy=False)
    cancelled = fields.Float("Quantity of cancelled product")
    combo_line_ids = fields.One2many('pos.prep.line', 'combo_parent_id')

    # PoS orderline computed fields, we cannot use related fields because the pos line can be deleted
    combo_parent_id = fields.Many2one('pos.prep.line', compute="_compute_combo_fields", store=True)
    product_id = fields.Many2one('product.product', compute="_compute_combo_fields", store=True)
    attribute_value_ids = fields.Many2many('product.template.attribute.value', compute="_compute_combo_fields", store=True)

    @api.depends('pos_order_line_id', 'pos_order_line_id.combo_line_ids', 'pos_order_line_id.combo_parent_id')
    def _compute_combo_fields(self):
        for line in self:
            pos_line = line.pos_order_line_id

            if pos_line.exists():
                line.attribute_value_ids = pos_line.attribute_value_ids

            if pos_line.product_id:
                line.product_id = pos_line.product_id

            if pos_line.combo_parent_id:
                related_pos_line = pos_line.combo_parent_id
                prep_lines = pos_line.combo_parent_id.prep_line_ids
                line.combo_parent_id = prep_lines.filtered(lambda pl: pl.pos_order_line_id == related_pos_line)

            if pos_line.combo_line_ids:
                related_pos_lines = pos_line.combo_line_ids
                prep_lines = pos_line.combo_line_ids.mapped('prep_line_ids')
                line.combo_line_ids = prep_lines.filtered(lambda pl: pl.pos_order_line_id in related_pos_lines)

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('prep_order_id', 'in', [order['id'] for order in data['pos.prep.order']])]
