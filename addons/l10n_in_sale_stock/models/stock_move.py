# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _l10n_in_get_product_price_unit(self):
        self.ensure_one()
        if (
            'bom_line_id' in self._fields and self.bom_line_id
            and self.bom_line_id.bom_id.type == 'phantom'
            and (kit_line := self.sale_line_id)
        ):
            return self._l10n_in_get_kit_component_price_unit(kit_line)
        if line_id := self.sale_line_id:
            if qty := line_id.product_uom_qty:
                company_id = line_id.company_id
                price = (
                    line_id.price_total if any(tax.price_include for tax in line_id.tax_id.flatten_taxes_hierarchy())
                    else line_id.price_subtotal
                )
                return line_id.currency_id._convert(
                    line_id.product_uom._compute_price(price / qty, self.product_uom),
                    company_id.currency_id,
                    company_id,
                    self.date,
                    round=False
                )
            return 0.00
        return super()._l10n_in_get_product_price_unit()

    def _l10n_in_get_kit_component_price_unit(self, kit_line):
        """Allocate this component's share of the Kit's SO line price,
        proportional to each component's own cost within the BoM."""
        self.ensure_one()
        bom = self.bom_line_id.bom_id
        sibling_lines = bom.bom_line_ids.filtered(lambda l: l.product_qty)
        # One batched read for all sibling products' costs, instead of one-per-line
        price_by_compoents = {
            p.id: p.standard_price
            for p in sibling_lines.mapped('product_id').with_company(self.company_id)
        }
        bom_line_costs = {
            l: l.product_qty * price_by_compoents[l.product_id.id]
            for l in sibling_lines
        }
        total_cost = sum(bom_line_costs.values())
        if not total_cost:
            return super()._l10n_in_get_product_price_unit()
        component_cost = bom_line_costs.get(self.bom_line_id, 0.0)
        kit_price = (
            kit_line.price_total if any(tax.price_include for tax in kit_line.tax_id.flatten_taxes_hierarchy())
            else kit_line.price_subtotal
        )
        allocated_total = kit_price * component_cost / total_cost
        return kit_line.currency_id._convert(
            kit_line.product_uom._compute_price(allocated_total / self.quantity, self.product_uom),
            self.company_id.currency_id,
            self.company_id,
            self.date,
            round=False
        )

    def _l10n_in_get_product_tax(self):
        self.ensure_one()
        if line_id := self.sale_line_id:
            return {
                'is_from_order': True,
                'taxes': line_id.tax_id,
            }
        return super()._l10n_in_get_product_tax()
