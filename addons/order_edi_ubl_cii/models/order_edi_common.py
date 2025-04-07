from odoo import _, models


class OrderEdiCommon(models.AbstractModel):
    _name = 'order.edi.common'
    _description = "Order EDI Common"

    # -------------------------------------------------------------------------
    # OVERRIDES
    # -------------------------------------------------------------------------

    def _get_order_qty_field(self):
        """Return the quantity field for the order type"""
        return

    def _get_dest_address_field(self):
        """Return the destination address field for the order type"""
        return

    def _get_order_type_code(self):
        """Return the order type code for the Order Transaction"""
        return
