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

    @api.one
    def _check_invoice_policy(self):
        if self.invoice_method == 'picking' and self.location_id.usage == 'customer':
            for proc in self.order_line.mapped('procurement_ids'):
                if proc.sale_line_id.order_id.order_policy == 'picking':
                    raise Warning(_('In the case of a dropship route, it is not possible to have an invoicing control set on "Based on incoming shipments" and a sale order with an invoice creation on "On Delivery Order"'))

    @api.multi
    def wkf_confirm_order(self):
        """ Raise a warning to forbid to have both purchase and sale invoices
        policies at delivery in dropshipping. As it is not implemented.

        This check can be disabled setting 'no_invoice_policy_check' in context
        """
        if not self.env.context.get('no_invoice_policy_check'):
            self._check_invoice_policy()
        super(purchase_order, self).wkf_confirm_order()

class procurement_order(models.Model):
    _inherit = 'procurement.order'

    @api.model
    def update_origin_po(self, po, proc):
        super(procurement_order, self).update_origin_po(po, proc)
        if proc.sale_line_id and not (proc.origin in po.origin):
            po.sudo().write({'origin': po.origin+', '+proc.origin})
