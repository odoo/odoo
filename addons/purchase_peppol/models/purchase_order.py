from odoo import models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_send_advanced_order(self):
        self.env['purchase.edi.xml.ubl_bis3_advanced_order'].send_xml(self)
