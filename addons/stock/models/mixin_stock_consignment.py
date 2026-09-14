from odoo import models

from ..tools import debug_log as dbg


class MixinStockConsignment(models.AbstractModel):
    _name = "mixin.stock.consignment"
    _description = "Set of Moves Handled as One Shipment"

    def _get_consignment_pickings(self):
        raise NotImplementedError

    def _get_consignment_moves(self):
        return self.move_ids

    def _get_consignment_move_lines(self):
        return self.move_line_ids

    def _get_consignment_partners(self):
        partners = self._get_consignment_pickings().partner_id
        dbg.logic.debug(
            "[consignment:%s] partners %s",
            dbg.rec(self),
            dbg.rec(partners),
        )
        return partners

    @dbg.timed
    def _get_consignment_weight(self):
        lines = self._get_consignment_move_lines()
        weight = sum(
            line.product_id.weight * line.quantity_product_uom for line in lines
        )
        dbg.logic.debug(
            "[consignment:%s] weight %s over %d move line(s)",
            dbg.rec(self),
            weight,
            len(lines),
        )
        return weight
