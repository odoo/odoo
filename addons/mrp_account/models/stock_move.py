# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_value_from_production(self, quantity):
        # TODO: Maybe move _cal_price here
        self.ensure_one()
        if not self.production_id:
            return super()._get_value_from_production(quantity)
        value = quantity * self.price_unit
        return {
            'value': value,
            'quantity': quantity,
            'description': self.env._('%(value)s for %(quantity)s %(unit)s from %(production)s',
                value=self.company_currency_id.format(value), quantity=quantity, unit=self.product_id.uom_id.name,
                production=self.production_id.display_name),
        }

    def _get_price_unit(self, product=None, include_consigned=False, include_consumable=False):
        """ Moves coming from a kit (phantom BoM) are valued per unit of the (root)
        kit: each storable component contributes its own unit value times the quantity
        of that component in one kit, as defined by the BoM. The delivered quantities
        do not have to add up to whole kits: the kit price only depends on the BoM
        composition, not on how the components were split across pickings.

        :param product: the kit product actually sold/moved. When set, its phantom BoM
            is used as the root kit directly. This disambiguates the case where the sold
            kit is itself a component of a larger kit: a move only stores its leaf
            ``bom_line_id``, so climbing the BoM tree from the moves would wrongly reach
            the larger kit. When not set, the moves are valued the standard way.
        :param include_consumable: also value the kit's consumable components (at their
            standard price); by default only storable components enter the kit cost.
        """
        kit_moves = self.filtered(lambda m: m.bom_line_id.bom_id.type == 'phantom')
        if not product or not kit_moves:
            return super()._get_price_unit(
                include_consigned=include_consigned, product=product, include_consumable=include_consumable,
            )

        root_bom = self.env['mrp.bom']._bom_find(product, bom_type='phantom')[product]
        if not root_bom:
            return product.standard_price

        kit_product = product
        _dummy, exploded_lines = root_bom.explode(kit_product, 1.0)
        qty_per_kit_by_line = defaultdict(float)
        for line, line_data in exploded_lines:
            qty_per_kit_by_line[line] += line.uom_id._compute_quantity(
                line_data['qty'], line.product_id.uom_id, round=False,
            ) / root_bom.uom_id._compute_quantity(root_bom.product_qty, kit_product.uom_id, round=False)

        price_unit = 0
        for bom_line, moves in kit_moves.grouped('bom_line_id').items():
            if not bom_line.product_id.is_storable and not include_consumable:
                continue
            component_price = super(StockMove, moves)._get_price_unit(
                include_consigned=include_consigned, include_consumable=include_consumable,
            )
            price_unit += component_price * qty_per_kit_by_line.get(bom_line, 0)
        return price_unit

    def _clear_journal_entries(self):
        account_moves = self.account_move_id
        account_moves.sudo().button_draft()
        account_moves.sudo().unlink()

    def _action_reset_to_assigned(self):
        self._clear_journal_entries()
        super()._action_reset_to_assigned()

    def _action_reset_to_draft(self):
        self._clear_journal_entries()
        super()._action_reset_to_draft()
