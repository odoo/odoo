# Part of Odoo. See LICENSE file for full copyright and licensing details.
from uuid import uuid4
from odoo import api, fields, models


class PosHistoryLine(models.Model):
    _name = 'pos.history.line'
    _description = "Point of Sale History Lines"
    _inherit = ["pos.load.mixin"]

    uuid = fields.Char(string='Uuid', readonly=True, default=lambda self: str(uuid4()), copy=False)
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)], required=True, change_default=True)
    price_unit = fields.Float(string='Unit Price', digits=0)
    qty = fields.Float('Quantity', digits='Product Unit', default=1)
    price_subtotal = fields.Monetary(string='Tax Excl.', readonly=True, required=True)
    price_subtotal_incl = fields.Monetary(string='Tax Incl.', readonly=True, required=True)
    price_extra = fields.Float(string="Price extra")
    attribute_value_ids = fields.Many2many('product.template.attribute.value', string="Selected Attributes")
    discount = fields.Float(string='Discount (%)', digits=0, default=0.0)

    # Relational fields
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id', string="Currency")
    product_uom_id = fields.Many2one('uom.uom', string='Product Unit', related='product_id.uom_id')
    tax_ids = fields.Many2many('account.tax', string='Taxes', readonly=True)
    tax_ids_after_fiscal_position = fields.Many2many('account.tax', compute='_get_tax_ids_after_fiscal_position', string='Taxes to Apply')
    order_id = fields.Many2one('pos.order', string='Order Ref', ondelete='cascade', required=True, index=True)

    combo_parent_id = fields.Many2one('pos.history.line', string='Combo Parent', index='btree_not_null')
    combo_line_ids = fields.One2many('pos.history.line', 'combo_parent_id', string='Combo Lines')
    combo_item_id = fields.Many2one('product.combo.item', string='Combo Item')

    _unique_uuid = models.Constraint('unique (uuid)', 'An order line with this uuid already exists')

    @api.depends('order_id', 'order_id.fiscal_position_id', 'tax_ids')
    def _get_tax_ids_after_fiscal_position(self):
        for line in self:
            line.tax_ids_after_fiscal_position = line.order_id.fiscal_position_id.map_tax(line.tax_ids)

    @api.model
    def _load_pos_data_domain(self, data, config):
        # Don't load any history line by default
        return [('id', '=', False)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['uuid', 'product_id', 'qty', 'price_unit', 'price_subtotal', 'price_subtotal_incl', 'combo_item_id', 'combo_parent_id', 'combo_line_ids', 'price_extra', 'attribute_value_ids', 'write_date', 'order_id', 'discount', 'tax_ids']

    def _get_discount_amount(self):
        self.ensure_one()
        original_price = self.tax_ids_after_fiscal_position.compute_all(self.price_unit, self.currency_id, self.qty, product=self.product_id, partner=self.order_id.partner_id)['total_included']
        return original_price - self.price_subtotal_incl
