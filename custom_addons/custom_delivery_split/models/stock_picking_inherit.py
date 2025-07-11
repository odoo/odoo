from odoo import models, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _split_picking_quantities(self, move):
        """
        Check available quantities in 'Split' location first (including nested locations),
        prioritizing SplitCase or Storage categories. Then pick the remaining quantity from the 'Full' location.
        """
        # Fetch Split and Full locations dynamically
        split_location = self.env['stock.location'].search([('name', '=', 'Divide')], limit=1)
        full_location = self.env['stock.location'].search([('name', '=', 'Full')], limit=1)


        # Get the total quantity to pick for the product
        total_qty_to_pick = move.product_uom_qty
        remaining_qty_to_pick = total_qty_to_pick

        # Step 1: Check available quantities in the Split location and its nested locations
        if split_location:
            split_available_qty = self._get_available_quantity_in_hierarchy(move.product_id, split_location, prioritize_split_case=True)
            print(f"Available in Split (including nested): {split_available_qty}")

            if split_available_qty > 0:
                qty_from_split = min(split_available_qty, remaining_qty_to_pick)
                self._create_move_line(move, split_location, qty_from_split)
                remaining_qty_to_pick -= qty_from_split
                print(f"Allocated {qty_from_split} from Split location: {split_location.name}")

        # Step 2: If more quantity is needed, allocate from the Full location and its nested locations
        if remaining_qty_to_pick > 0 and full_location:
            full_available_qty = self._get_available_quantity_in_hierarchy(move.product_id, full_location)
            print(f"Available in Full (including nested): {full_available_qty}")

            if full_available_qty > 0:
                qty_from_full = min(remaining_qty_to_pick, full_available_qty)
                self._create_move_line(move, full_location, qty_from_full)
                print(f"Allocated {qty_from_full} from Full location: {full_location.name}")

        # Final print for debugging
        if remaining_qty_to_pick > 0:
            print(f"Could not fully allocate, remaining qty: {remaining_qty_to_pick}")
        else:
            print(f"Successfully allocated all quantities for move.")

    def _create_move_line(self, move, location, qty):
        """Helper method to create stock move lines for specific quantities and locations."""
        self.env['stock.move.line'].create({
            'move_id': move.id,
            'location_id': location.id,
            'product_id': move.product_id.id,
            'product_uom_qty': qty,
            'product_uom_id': move.product_uom.id,
            'location_dest_id': move.location_dest_id.id,
        })

    def _get_available_quantity_in_hierarchy(self, product, location, prioritize_split_case=False):
        """
        Helper method to check the available quantity of a product in a given location and its child locations.
        Uses the `child_of` operator to consider nested locations. Can prioritize SplitCase or specific storage categories.
        """
        # Fetch all quants for the product in the location hierarchy
        quants = self.env['stock.quant'].search([
            ('product_id', '=', product.id),
            ('location_id', 'child_of', location.id)  # Include nested locations
        ])

        if prioritize_split_case:
            # Prioritize quants in locations with SplitCase or specific categories (adjust logic as needed)
            prioritized_quants = quants.filtered(lambda q: q.location_id.storage_category == 'SplitCase')
            if prioritized_quants:
                return sum(quant.quantity for quant in prioritized_quants)

        # Return sum of available quantities across all quants in the location hierarchy
        return sum(quant.quantity for quant in quants)

    @api.model
    def _action_assign(self):
        """
        Override the action assign method to apply the split picking logic
        when confirming the sales order.
        """
        res = super(StockPicking, self)._action_assign()
        for move in self.move_lines:
            self._split_picking_quantities(move)
        return res
