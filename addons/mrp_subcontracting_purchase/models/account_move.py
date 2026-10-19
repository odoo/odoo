from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_price_difference_lines_vals(self):
        """ For a subcontracted product, the standard price only covers the subcontracting
        service: add the cost of the components consumed by the subcontractor to the price
        difference computed by `super()`, apportioned to this bill's quantity.
        """
        lines_vals_list = super()._get_price_difference_lines_vals()
        for line in self.invoice_line_ids:
            if line.product_id.cost_method != 'standard' or not line.purchase_line_id:
                continue
            matches = [vals for vals in lines_vals_list if vals.get('cogs_origin_id') == line.id]
            if not matches:
                continue
            pdiff_vals, correction_vals = matches

            subcontract_production = line.purchase_line_id.move_ids._get_subcontract_production()
            components_cost = sum(subcontract_production.move_raw_ids.mapped('value'))
            qty = sum(
                mo.uom_id._compute_quantity(mo.qty_producing, line.product_uom_id)
                for mo in subcontract_production if mo.state == 'done'
            )
            if line.product_uom_id.is_zero(qty):
                continue

            delta = self.company_currency_id.round(self.direction_sign * components_cost * line.quantity / qty)
            if self.company_currency_id.is_zero(delta):
                continue
            pdiff_vals['balance'] -= delta
            correction_vals['balance'] += delta
        return lines_vals_list

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        production_ids = set()
        for move in posted:
            if not move.is_purchase_document():
                continue
            mos = move.invoice_line_ids.purchase_line_id.move_ids._get_subcontract_production()
            production_ids.update(mos.filtered(lambda p: p.state == 'done').ids)
        self.env['mrp.production'].browse(production_ids)._post_subcontract_extra_cost()
        return posted
