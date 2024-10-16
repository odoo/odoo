# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import project_purchase


class PurchaseOrder(project_purchase.PurchaseOrder):

    def _prepare_picking(self):
        res = super()._prepare_picking()
        if not self.project_id:
            return res
        return {
            **res,
            'project_id': self.project_id.id,
        }
