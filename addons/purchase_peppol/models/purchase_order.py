from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    peppol_order_id = fields.Char(string="PEPPOL order document ID")
    order_change_sequence_no = fields.Integer(default=0)

    def action_send_advanced_order(self):
        self.env['purchase.edi.xml.ubl_bis3_order']._send_xml(self)

    def action_send_order_cancel(self):
        self.env['purchase.edi.xml.ubl_bis3_order_cancel'].build_order_cancel_xml(self)
