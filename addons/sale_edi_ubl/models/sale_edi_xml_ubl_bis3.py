from odoo import models


class SaleEdiXmlUbl_Bis3(models.AbstractModel):
    _name = 'sale.edi.xml.ubl_bis3'
    _inherit = ['order.edi.xml.ubl_bis3']
    _description = "Sale BIS Ordering 3.0"

    def _get_order_qty_field(self):
        return 'product_uom_qty'

    def _get_dest_address_field(self):
        return 'partner_shipping_id'

    def _get_order_type_code(self):
        return 220

    def _get_order_type(self):
        return 'sale'

    def _get_order_ref(self):
        return 'client_order_ref'

    def _get_order_partner_role(self):
        return "BuyerCustomer"

    def _import_order_ubl(self, order, file_data):
        # Overriding the main method to recalculate the price unit and discount
        res = super()._import_order_ubl(order, file_data)
        lines_with_products = order.order_line.filtered('product_id')
        # Recompute product price and discount according to sale price
        lines_with_products._compute_price_unit()
        lines_with_products._compute_discount()
        return res
