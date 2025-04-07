from odoo import models


class PurchaseEdiXmlUbl_Bis3(models.AbstractModel):
    _name = 'purchase.edi.xml.ubl_bis3'
    _inherit = ['order.edi.xml.ubl_bis3']
    _description = "Purchase UBL BIS Ordering 3.0"

    def _get_order_qty_field(self):
        return 'product_qty'

    def _get_dest_address_field(self):
        return 'dest_address_id'

    def _get_order_type_code(self):
        return 105
