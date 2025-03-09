from odoo import models, fields, api

import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    total_custom_price_1 = fields.Monetary(string="Totale Prezzo 2", compute="_compute_totals", store=True)
    total_custom_price_2 = fields.Monetary(string="Totale Prezzo 3", compute="_compute_totals", store=True)

    custom_sale_order_template_id = fields.Many2one('sale.order.template', string='Aggiungi da modello', store=False)

    @api.depends("order_line", "order_line.custom_price_1", "order_line.custom_price_2")
    def _compute_totals(self):
        for order in self:
            order.total_custom_price_1 = sum(line.custom_price_1*line.product_uom_qty or 0.0 for line in order.order_line)
            order.total_custom_price_2 = sum(line.custom_price_2*line.product_uom_qty or 0.0 for line in order.order_line)

    @api.onchange('total_custom_price_1', 'total_custom_price_2')
    def _onchange_custom_prices(self):
        _logger.debug("************ CUSTOM _onchange_custom_prices")
        self._compute_amounts()

    #TBD - non ha effetto a video, ma sembra funzionare sulla griglia
    @api.depends('order_line.price_subtotal', 'currency_id', 'company_id', 'order_line.custom_price_1','order_line.custom_price_2')
    def _compute_amounts(self):
        _logger.debug("************ CUSTOM _compute_amounts")
        super(SaleOrder, self)._compute_amounts()
        for order in self:
            order.amount_untaxed += order.total_custom_price_1 + order.total_custom_price_2
            order.amount_total = order.amount_untaxed + order.amount_tax


    @api.onchange('custom_sale_order_template_id')
    def _onchange_custom_sale_order_template(self):
        if self.custom_sale_order_template_id:
            _logger.info(
                f"Selected Quotation Template: {self.custom_sale_order_template_id.name} with ID {self.custom_sale_order_template_id.id}")

            # Prepare the new lines
            new_lines = []

            for line in self.custom_sale_order_template_id.sale_order_template_line_ids:
                if line.product_id:  # If the line has a product, it's a product line
                    product = line.product_id
                    new_lines.append((0, 0, {
                        'product_id': product.id,
                        'name': product.display_name,
                        'product_uom_qty': line.product_uom_qty,
                        'price_unit': product.lst_price,
                        'custom_price_1': product.product_tmpl_id.custom_price_1,
                        'custom_price_2': product.product_tmpl_id.custom_price_2
                    }))
                else:  # If there's no product, it's a section line
                    new_lines.append((0, 0, {
                        'name': line.name,  # Use the section's name
                        'display_type': 'line_section',  # This makes it a section row
                        'sequence': line.sequence or 10,  # Use the template's sequence or default to 10
                    }))

            # Append the new lines to the existing order lines
            if new_lines:
                self.order_line = [(4, line.id) for line in self.order_line] + new_lines
            else:
                _logger.warning("No new lines to add.")
        else:
            _logger.warning("Quotation Template not selected.")
