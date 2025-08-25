from odoo import api, models, _
from odoo.exceptions import UserError


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        for vals, lot_valuated in zip(vals_list, self.env['product.product'].browse([value['product_id'] for value in vals_list]).mapped('lot_valuated')):
            if not lot_valuated:
                continue
            if not vals.get('lot_id', True) and not vals.get('lot_name', True):
                products_list = self.env['product.product'].browse([value['product_id'] for value in vals_list]).filtered(lambda product: product.lot_valuated)
                string_products_list = "\n".join(f"- {product_name}" for product_name in products_list.mapped("display_name"))
                raise UserError(
                    _("You need to supply a Lot/Serial Number for lot valuated product:\n%(products)s",
                        products=string_products_list,
                    ))
        mls = super().create(vals_list)
        if any(move.is_valued for move in mls.move_id):
            mls.move_id._set_value()
        return mls

    def write(self, vals):
        if ('lot_id' in vals or 'lot_name' in vals) and any(self.product_id.mapped('lot_valuated')):
            if not vals.get('lot_id', False) and not vals.get('lot_name', False):
                products_list = self.product_id.filtered(lambda product: product.lot_valuated)
                string_products_list = "\n".join(f"- {product_name}" for product_name in products_list.mapped("display_name"))
                raise UserError(
                    _("You need to supply a Lot/Serial Number for lot valuated product:\n%(products)s",
                        products=string_products_list,
                    ))
        move_to_update = set()
        valuation_fields = ['qty_done', 'location_id', 'location_dest_id', 'owner_id', 'quant_id', 'lot_id']
        valuation_trigger = any(field in vals for field in valuation_fields)
        if valuation_trigger:
            move_to_update.update(self.move_id.filtered(lambda m: m.is_valued).ids)
        res = super().write(vals)
        if valuation_trigger:
            move_to_update.update(self.move_id.filtered(lambda m: m.is_valued).ids)
        if move_to_update:
            self.env['stock.move'].browse(move_to_update)._set_value()
        return res

    @api.model
    def _should_exclude_for_valuation(self):
        """
        Determines if this move line should be excluded from valuation based on its ownership.
        :return: True if the move line's owner is different from the company's partner (indicating
                it should be excluded from valuation), False otherwise.
        """
        self.ensure_one()
        return self.owner_id and self.owner_id != self.company_id.partner_id
