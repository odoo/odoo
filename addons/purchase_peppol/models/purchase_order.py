from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    order_change_sequence_no = fields.Integer(default=0)

    def action_send_advanced_order(self):
        self.env['purchase.edi.xml.ubl_bis3_order']._send_xml(self)
