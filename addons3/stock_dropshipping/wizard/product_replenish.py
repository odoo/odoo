# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv import expression


class ProductReplenish(models.TransientModel):
    _inherit = 'product.replenish'

    def _get_allowed_route_domain(self):
        domains = super()._get_allowed_route_domain()
        return expression.AND([domains, [('id', '!=', self.env.ref('stock_dropshipping.route_drop_shipping', raise_if_not_found=False).id)]])
