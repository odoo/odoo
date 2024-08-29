from odoo import models
from odoo.addons import purchase


class PurchaseOrder(models.Model, purchase.PurchaseOrder):

    def _get_edi_builders(self):
        return super()._get_edi_builders() + [self.env['purchase.edi.xml.ubl_bis3']]
