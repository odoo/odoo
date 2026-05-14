from odoo import models


class StockAssignSerialNumbers(models.TransientModel):
    _inherit = 'stock.assign.serial'

    def _assign_serial_numbers(self, cancel_remaining_quantity=False):
        if (
            not self.production_id._get_subcontract_move()
            or self.production_id.product_id.tracking != 'serial'
        ):
            return super()._assign_serial_numbers(cancel_remaining_quantity)
        serial_numbers = set(self._get_serial_numbers())
        res = super()._assign_serial_numbers(cancel_remaining_quantity)
        if not serial_numbers:
            return res
        productions = (
            self.production_id.procurement_group_id.mrp_production_ids.filtered(
                lambda mo: mo.state not in ('done', 'cancel')
                and not mo.subcontracting_has_been_recorded
                and mo._get_subcontract_move()
                and mo.lot_producing_id
                and mo.lot_producing_id.name in serial_numbers
            )
        )
        for production in productions:
            subcontract_move = production._get_subcontract_move().filtered(
                lambda m: m.state not in ('done', 'cancel')
            )[:1]
            if subcontract_move:
                subcontract_move._auto_record_components(production.product_qty)
        return res
