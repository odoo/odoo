from odoo import api, fields, models, tools, _
from odoo.osv.expression import AND


class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.model
    def search_paid_order_ids(self, config_id, domain, limit, offset):
        """Search for 'paid' orders that satisfy the given domain, limit and offset."""
        default_domain = ['&', ('config_id', '=', config_id), '!', '|', ('state', '=', 'draft'),
                          ('state', '=', 'cancelled')]
        if domain:
            domain = ['|'] + domain + [['lines.product_id.name', 'ilike', domain[2][2]]]
        real_domain = AND([domain, default_domain])
        ids = self.search(AND([domain, default_domain]), limit=limit, offset=offset).ids
        totalCount = self.search_count(real_domain)
        return {'ids': ids, 'totalCount': totalCount}
