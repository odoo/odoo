# coding: utf-8

from openerp import models, api


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def _check_routing(self, product, warehouse):
        """ skip stock verification if the route goes from supplier to customer
            As the product never goes in stock, no need to verify it's availibility
        """
        res = super(sale_order_line, self)._check_routing(product, warehouse)
        if not res:
            for line in self:
                for pull_rule in line.route_id.pull_ids:
                    if (pull_rule.picking_type_id.default_location_src_id.usage == 'supplier' and
                            pull_rule.picking_type_id.default_location_dest_id.usage == 'customer'):
                        res = True
                        break
        return res
