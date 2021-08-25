from odoo import models, fields


class PurchaseOrderLine(models.Model):
    _inherit = 'res.partner'

    marketplace_id = fields.Integer("Reference marketplace")
    is_in_marketplace = fields.Boolean("From marketplace?", compute="_compute_is_from_marketplace")

    def _compute_is_from_marketplace(self):
        if self.marketplace_id:
            self.is_in_marketplace = True
            return
        self.is_in_marketplace = False
