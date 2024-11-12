from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _get_edi_builders(self):
        return super()._get_edi_builders() + [self.env['purchase.edi.xml.ubl_bis3']]
