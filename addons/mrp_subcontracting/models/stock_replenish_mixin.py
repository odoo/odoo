# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import stock

from odoo import models, _
from odoo.osv import expression


class StockReplenishMixin(models.AbstractModel, stock.StockReplenishMixin):

    def _get_allowed_route_domain(self):
        domains = super()._get_allowed_route_domain()
        route_id = self.env['stock.warehouse']._find_or_create_global_route('mrp_subcontracting.route_resupply_subcontractor_mto', _('Resupply Subcontractor on Order')).id
        return expression.AND([domains, [('id', '!=', route_id)]])
