from odoo import fields, models, api
from uuid import uuid4


class PosPrepLine(models.Model):
    _name = 'pos.prep.line'
    _description = 'Pos Preparation Line'
    _inherit = ['pos.load.mixin']

    prep_order_id = fields.Many2one('pos.prep.order', string='Preparation Order', required=True, ondelete='cascade', index='btree_not_null')
    quantity = fields.Float('Quantity', required=True)
    pos_order_line_uuid = fields.Char(help="Original pos order line UUID")
    pos_order_line_id = fields.Many2one('pos.order.line', string="Original pos order line")
    uuid = fields.Char(string='Uuid', readonly=True, default=lambda self: str(uuid4()), copy=False)
    cancelled = fields.Float("Quantity of cancelled product")
    co_prep_line_id = fields.Many2one('pos.prep.line', string="Original preparation line", index='btree_not_null')
    attribute_value_ids = fields.Many2many('product.template.attribute.value', 'pos_prep_line_product_template_attribute_value_rel', string="Selected Attributes")
    product_id = fields.Many2one('product.product', string="Product ID")
    combo_line_ids = fields.One2many('pos.prep.line', 'combo_parent_id', string="Combo Lines")
    combo_parent_id = fields.Many2one('pos.prep.line', string="Parent Combo Line", help="Indicates the parent line if this is part of a combo", index='btree_not_null')

    @api.model_create_multi
    def create(self, vals_list):
        prepLines = super().create(vals_list)
        for pl in prepLines:
            if not pl.pos_order_line_id:
                orderLine = self.env['pos.order.line'].search([('uuid', '=', pl.pos_order_line_uuid)])
                pl.pos_order_line_id = orderLine.id
        return prepLines
