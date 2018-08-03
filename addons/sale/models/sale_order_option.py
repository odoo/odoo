from odoo import api, fields, models
from odoo.tools.translate import html_translate
from odoo.addons import decimal_precision as dp


class SaleOrderOption(models.Model):
    _name = "sale.order.option"
    _description = "Sale Options"
    _order = 'sequence, id'

    order_id = fields.Many2one('sale.order', 'Sales Order Reference', ondelete='cascade', index=True)
    line_id = fields.Many2one('sale.order.line', on_delete="set null")
    name = fields.Text('Description', required=True)
    product_id = fields.Many2one('product.product', 'Product', domain=[('sale_ok', '=', True)])
    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Product Price'))
    discount = fields.Float('Discount (%)', digits=dp.get_precision('Discount'))
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure ', required=True)
    quantity = fields.Float('Quantity', required=True, digits=dp.get_precision('Product UoS'), default=1)
    sequence = fields.Integer('Sequence', help="Gives the sequence order when displaying a list of suggested product.")

    @api.onchange('product_id', 'uom_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        product = self.product_id.with_context(lang=self.order_id.partner_id.lang)
        self.price_unit = product.list_price
        self.name = product.name
        if product.description_sale:
            self.name += '\n' + product.description_sale
        self.uom_id = self.uom_id or product.uom_id
        pricelist = self.order_id.pricelist_id
        if pricelist and product:
            partner_id = self.order_id.partner_id.id
            self.price_unit = pricelist.with_context(uom=self.uom_id.id).get_product_price(product, self.quantity, partner_id)
        domain = {'uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        return {'domain': domain}

    @api.multi
    def button_add_to_order(self):
        self.ensure_one()
        order = self.order_id
        if order.state not in ['draft', 'sent']:
            return False

        order_line = order.order_line.filtered(lambda line: line.product_id == self.product_id)
        if order_line:
            order_line = order_line[0]
            order_line.product_uom_qty += 1
        else:
            vals = self._get_vals_add_to_order()
            order_line = self.env['sale.order.line'].create(vals)
            order_line._compute_tax_id()

        self.write({'line_id': order_line.id})
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def _get_vals_add_to_order(self):
        return {
            'price_unit': self.price_unit,
            'name': self.name,
            'order_id': self.order_id.id,
            'product_id': self.product_id.id,
            'product_uom_qty': self.quantity,
            'product_uom': self.uom_id.id,
            'discount': self.discount,
        }
