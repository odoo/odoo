from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = "sale.order"

    total_custom_field_1 = fields.Monetary(string="Totale Prezzo 2", compute="_compute_totals", store=True)
    total_custom_field_2 = fields.Monetary(string="Totale Prezzo 3", compute="_compute_totals", store=True)
    total_custom_field_3 = fields.Monetary(string="Totale Prezzo 4", compute="_compute_totals", store=True)

    @api.depends("order_line", "order_line.custom_field_1", "order_line.custom_field_2", "order_line.custom_field_3")
    def _compute_totals(self):
        for order in self:
            order.total_custom_field_1 = sum(line.custom_field_1*line.product_uom_qty or 0.0 for line in order.order_line)
            order.total_custom_field_2 = sum(line.custom_field_2*line.product_uom_qty or 0.0 for line in order.order_line)
            order.total_custom_field_3 = sum(line.custom_field_3*line.product_uom_qty or 0.0 for line in order.order_line)
    
    @api.depends("order_line", "order_line.custom_field_1", "order_line.custom_field_2", "order_line.custom_field_3","amount_untaxed", "amount_tax", "total_custom_field_1", "total_custom_field_2", "total_custom_field_3")
    def _compute_amounts(self):
        super(SaleOrder, self)._compute_amounts()
        """ Override Odoo's standard total calculation to include custom totals """
        for order in self:
           additional_total = order.total_custom_field_1 + order.total_custom_field_2 + order.total_custom_field_3
           order.amount_total = order.amount_untaxed + order.amount_tax + additional_total