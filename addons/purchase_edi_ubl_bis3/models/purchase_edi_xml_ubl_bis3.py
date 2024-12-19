from lxml import etree

from odoo import models, _
from odoo.tools import html2plaintext, cleanup_xml_node


class PurchaseEdiXmlUbl_Bis3(models.AbstractModel):
    _name = 'purchase.edi.xml.ubl_bis3'
    _inherit = ['order.edi.xml.ubl_bis3']
    _description = "Purchase UBL BIS Ordering 3.0"

    def _get_order_type(self):
        return 'purchase'

    def _get_order_qty_field(self):
        return 'product_qty'

    def _get_order_tax_field(self):
        return 'taxes_id'

    def _get_order_note_field(self):
        return 'notes'

    def _get_dest_address_field(self):
        return 'dest_address_id'

    def _get_order_type_code(self):
        return 105

    def _get_order_ref(self):
        return 'partner_ref'

    def _get_order_partner_role(self):
        return "SellerSupplier"
