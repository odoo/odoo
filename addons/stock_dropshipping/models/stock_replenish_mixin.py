# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.fields import Domain


class StockReplenishMixin(models.AbstractModel):
    _inherit = 'stock.replenish.mixin'

    def _get_allowed_route_domain(self):
        domains = super()._get_allowed_route_domain()
        return Domain.AND([domains, [('id', '!=', self.env.ref('stock_dropshipping.route_drop_shipping', raise_if_not_found=False).id)]])
