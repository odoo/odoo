from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    custom_price_1 = fields.Monetary(string="Prezzo 2", store=True)
    custom_price_2 = fields.Monetary(string="Prezzo 3", store=True)

    @api.onchange('product_id')
    def _onchange_product_id_custom_price(self):
        if self.product_id:
            self.custom_price_1 = self.product_id.product_tmpl_id.custom_price_1
            self.custom_price_2 = self.product_id.product_tmpl_id.custom_price_2

    @api.depends("product_id", "product_uom_qty", "custom_price_1", "custom_price_2", "price_unit")
    def _compute_amount(self):
        """ Override Odoo's standard price_subtotal calculation """
        super(SaleOrderLine, self)._compute_amount()  # Keep Odoo's original logic

        for line in self:
            additional_price = (line.custom_price_1 or 0.0) + (line.custom_price_2 or 0.0)
            line.price_subtotal = (line.price_unit + additional_price) * line.product_uom_qty