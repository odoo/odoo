from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    custom_field_1 = fields.Monetary(string="Prezzo 2", store=True)
    custom_field_2 = fields.Monetary(string="Prezzo 3", store=True)
    custom_field_3 = fields.Monetary(string="Prezzo 4", store=True)
    tax_percent = fields.Float(string="Tax (%)", compute="_compute_tax_percent", store=True)

    @api.depends("product_id")
    def _compute_custom_fields(self):
        for line in self:
            if line.product_id:
                line.custom_field_1 = line.product_id.list_price or 0.0
                line.custom_field_2 = line.product_id.standard_price or 0.0
                line.custom_field_3 = line.product_id.weight or 0.0
            else:
                line.custom_field_1 = 0.0
                line.custom_field_2 = 0.0
                line.custom_field_3 = 0.0

    @api.depends("product_id", "product_uom_qty", "custom_field_1", "custom_field_2", "custom_field_3", "price_unit")
    def _compute_amount(self):
        """ Override Odoo's standard price_subtotal calculation """
        super(SaleOrderLine, self)._compute_amount()  # Keep Odoo's original logic

        for line in self:
            additional_price = (line.custom_field_1 or 0.0) + (line.custom_field_2 or 0.0) + (line.custom_field_3 or 0.0)
            line.price_subtotal = (line.price_unit + additional_price) * line.product_uom_qty
            
            
    @api.depends("tax_id")
    def _compute_tax_percent(self):
        """Compute the tax percentage from the first applied tax"""
        for line in self:
            line.tax_percent = line.tax_id[:1].amount if line.tax_id else 0.0