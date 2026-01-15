# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # ========== Fields ==========
    
    product_volume = fields.Float(
        string="Volume",
        related='product_id.volume',
        readonly=True,
        store=False,
        digits='Volume',
        help="Product volume from product template"
    )
    
    number_of_panels = fields.Float(
        string="Number of Panels",
        digits='Product Unit',
        default=0.0,
        help="Number of panels - this value will be multiplied by quantity. If 0 or empty, it will not affect calculations."
    )
    
    effective_quantity = fields.Float(
        string="Effective Quantity",
        compute='_compute_effective_quantity',
        store=True,
        digits='Product Unit',
        help="Effective quantity = number of panels × quantity. If number of panels = 0, uses normal quantity."
    )

    # ========== Compute Methods ==========

    @api.depends('number_of_panels', 'product_uom_qty')
    def _compute_effective_quantity(self):
        """
        Calculate effective quantity based on number of panels × quantity
        If number_of_panels = 0 or empty, uses normal product_uom_qty
        """
        for line in self:
            if line.number_of_panels and line.number_of_panels > 0:
                line.effective_quantity = line.number_of_panels * line.product_uom_qty
            else:
                line.effective_quantity = line.product_uom_qty

    # ========== Override Methods (Safe) ==========

    def _prepare_base_line_for_taxes_computation(self, **kwargs):
        """
        Safe override: uses effective_quantity in financial calculations only
        If number_of_panels = 0 or empty, uses normal product_uom_qty (no impact)
        """
        base_values = super()._prepare_base_line_for_taxes_computation(**kwargs)
        # Use effective_quantity only if number_of_panels > 0
        if self.number_of_panels and self.number_of_panels > 0:
            base_values['quantity'] = self.effective_quantity
        # If number_of_panels = 0 or empty, uses normal product_uom_qty (no impact)
        return base_values

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_ids', 'number_of_panels', 'effective_quantity')
    def _compute_amount(self):
        """
        Safe override: uses effective_quantity in calculations only
        If number_of_panels = 0 or empty, uses normal product_uom_qty
        """
        # Call super first to get basic calculations
        super()._compute_amount()
        
        # Modify calculations only if number_of_panels > 0
        lines_to_recompute = self.filtered(lambda l: l.number_of_panels and l.number_of_panels > 0)
        if not lines_to_recompute:
            return
        
        AccountTax = self.env['account.tax']
        for line in lines_to_recompute:
            # Recalculate price_subtotal and price_total using effective_quantity
            company = line.company_id or self.env.company
            base_line = line._prepare_base_line_for_taxes_computation()
            AccountTax._add_tax_details_in_base_line(base_line, company)
            AccountTax._round_base_lines_tax_details([base_line], company)
            line.price_subtotal = base_line['tax_details']['total_excluded_currency']
            line.price_total = base_line['tax_details']['total_included_currency']
            line.price_tax = line.price_total - line.price_subtotal

    def _prepare_invoice_line(self, **optional_values):
        """
        Safe override: uses effective_quantity in Invoice Line
        If number_of_panels = 0 or empty, uses normal product_uom_qty
        """
        res = super()._prepare_invoice_line(**optional_values)
        # Use effective_quantity only if number_of_panels > 0
        if self.number_of_panels and self.number_of_panels > 0:
            res['quantity'] = self.effective_quantity
            # Add number_of_panels information in description (optional)
            if res.get('name'):
                res['name'] = f"{res['name']}\nNumber of Panels: {self.number_of_panels}"
        return res
