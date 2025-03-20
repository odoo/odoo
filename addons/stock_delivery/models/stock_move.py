# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.sql import column_exists, create_column


class StockRoute(models.Model):
    _inherit = "stock.route"

    shipping_selectable = fields.Boolean("Applicable on Shipping Methods")


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _auto_init(self):
        if not column_exists(self.env.cr, "stock_move", "weight"):
            # In case of a big database with a lot of stock moves, the RAM gets exhausted
            # To prevent a process from being killed We create the column 'weight' manually
            # Then we do the computation in a query by multiplying product weight with qty
            create_column(self.env.cr, "stock_move", "weight", "numeric")
            self.env.cr.execute("""
                UPDATE stock_move move
                SET weight = move.product_qty * product.weight
                FROM product_product product
                WHERE move.product_id = product.id
                AND move.state != 'cancel'
                """)
        return super()._auto_init()

    weight = fields.Float(compute='_cal_move_weight', digits='Stock Weight', store=True, compute_sudo=True)

    @api.depends('product_id', 'product_uom_qty', 'product_uom')
    def _cal_move_weight(self):
        moves_with_weight = self.filtered(lambda moves: moves.product_id.weight > 0.00)
        for move in moves_with_weight:
            move.weight = (move.product_qty * move.product_id.weight)
        (self - moves_with_weight).weight = 0

    def _get_new_picking_values(self):
        vals = super(StockMove, self)._get_new_picking_values()
        carrier_id = self.reference_ids.sale_ids.carrier_id.id
        carrier_tracking_ref = False
        if self.move_orig_ids.picking_id.carrier_id:
            # check if previous picking have carrier_id take carrier from that
            # earlier we were taking carrier from sale but since carrier can be changed  or updated in next steps so now we take carrier from prev picking
            carrier_id = self.move_orig_ids.picking_id.carrier_id.id
            carrier_tracking_ref = self.move_orig_ids.picking_id.carrier_tracking_ref
        # propagating carrier and tracking ref only if carrier propagation rule allow
        if any(rule.propagate_carrier for rule in self.rule_id):
            vals['carrier_tracking_ref'] = carrier_tracking_ref
            vals['carrier_id'] = carrier_id
        return vals

    def _key_assign_picking(self):
        keys = super(StockMove, self)._key_assign_picking()
        return keys + (self.sale_line_id.order_id.carrier_id,)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    sale_price = fields.Float(compute='_compute_sale_price')
    destination_country_code = fields.Char(related='picking_id.destination_country_code')
    carrier_id = fields.Many2one(related='picking_id.carrier_id')

    @api.depends('quantity', 'product_uom_id', 'product_id', 'move_id.sale_line_id', 'move_id.sale_line_id.price_reduce_taxinc', 'move_id.sale_line_id.product_uom_id')
    def _compute_sale_price(self):
        for move_line in self:
            sale_line_id = move_line.move_id.sale_line_id
            if sale_line_id and sale_line_id.product_id == move_line.product_id:
                unit_price = sale_line_id.price_reduce_taxinc
                qty = move_line.product_uom_id._compute_quantity(move_line.quantity, sale_line_id.product_uom_id)
            else:
                # For kits, use the regular unit price
                unit_price = move_line.product_id.list_price
                qty = move_line.product_uom_id._compute_quantity(move_line.quantity, move_line.product_id.uom_id)
            move_line.sale_price = unit_price * qty
        super(StockMoveLine, self)._compute_sale_price()

    def _get_aggregated_product_quantities(self, **kwargs):
        """Returns dictionary of products and corresponding values of interest + hs_code

        Unfortunately because we are working with aggregated data, we have to loop through the
        aggregation to add more values to each datum. This extension adds on the hs_code value.

        returns: dictionary {same_key_as_super: {same_values_as_super, hs_code}, ...}
        """
        aggregated_move_lines = super()._get_aggregated_product_quantities(**kwargs)
        for aggregated_move_line in aggregated_move_lines:
            hs_code = aggregated_move_lines[aggregated_move_line]['product'].product_tmpl_id.hs_code
            aggregated_move_lines[aggregated_move_line]['hs_code'] = hs_code
        return aggregated_move_lines

    def _pre_put_in_pack_hook(self, all_lines=False, package_id=False, package_type_id=False, package_name=False, from_package_wizard=False):
        res = super()._pre_put_in_pack_hook(all_lines, package_id, package_type_id, package_name, from_package_wizard)
        if res and not from_package_wizard and self.carrier_id:
            context = res.get('context', {})
            context['default_package_carrier_type'] = self._get_package_carrier_type_for_pack()
            res['context'] = context
        return res

    def _post_put_in_pack_hook(self, package):
        weight = self.env.context.get('weight')
        if weight:
            package.shipping_weight = weight
        return super()._post_put_in_pack_hook(package)

    def _get_package_carrier_type_for_pack(self):
        if len(self.carrier_id) > 1 or any(not ml.carrier_id for ml in self):
            # avoid (duplicate) costs for products
            raise UserError(self.env._("You cannot pack products into the same package when they have different carriers (i.e. check that all of their transfers have a carrier assigned and are using the same carrier)."))

        # As we pass the `delivery_type` ('fixed' or 'base_on_rule' by default) in a key that
        # corresponds to the `package_carrier_type` (defaults to 'none'), we do a conversion.
        # No need to convert for other carriers as the `delivery_type` and
        # `package_carrier_type` will be the same in these cases.
        package_carrier_type = self.carrier_id.delivery_type
        if package_carrier_type in ['fixed', 'base_on_rule']:
            package_carrier_type = 'none'
        return package_carrier_type

    def _should_set_package(self):
        if self.carrier_id:
            return True
        return super()._should_set_package()
