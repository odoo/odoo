from odoo import models, Command


class SaleEdiXmlUbl_Bis3(models.AbstractModel):
    _name = 'sale.edi.xml.ubl_bis3'
    _inherit = ['order.edi.xml.ubl_bis3']
    _description = "Sale UBL BIS Ordering 3.0"

    def _get_order_type(self):
        return 'sale'

    def _get_order_qty_field(self):
        return 'product_uom_qty'

    def _get_order_tax_field(self):
        return 'tax_ids'

    def _get_order_note_field(self):
        return 'note'

    def _get_dest_address_field(self):
        return 'partner_shipping_id'

    def _get_order_type_code(self):
        return 220

    def _get_order_ref(self):
        return 'client_order_ref'
