# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _check_delivery_address(self, **kwargs):
        self.ensure_one()
        # skip check for mondialrelay partners as the customer can not edit them
        if self.is_mondialrelay:
            return True
        return super()._check_delivery_address(**kwargs)
