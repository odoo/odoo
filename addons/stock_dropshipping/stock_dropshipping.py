# coding: utf-8

from openerp import models, api, _
from openerp.exceptions import Warning


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


class purchase_order(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def wkf_confirm_order(self):
        for po in self:
            if po.invoice_method == 'picking' and po.location_id.usage == 'customer':
                for proc in po.order_line.mapped('procurement_ids'):
                    if proc.sale_line_id.order_id.order_policy == 'picking':
                        raise Warning(_('In the case of a dropship route, it is not possible to have an invoicing control set on "Based on incoming shipments" and a sale order with an invoice creation on "On Delivery Order"'))
        super(purchase_order, self).wkf_confirm_order()
