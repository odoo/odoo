# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import float_compare


class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'

    purchase_requisition_id = fields.Many2one('purchase.requisition', related='purchase_requisition_line_id.requisition_id', string='Agreement')
    purchase_requisition_line_id = fields.Many2one('purchase.requisition.line', index='btree_not_null')

    def write(self, vals):
        res = super().write(vals)
        if ('date_start' in vals or 'date_end' in vals) and not self.env.context.get('syncing_blanket_order_dates'):
            # keep the validity of the blanket order in sync with its pricelists
            for supplierinfo in self.filtered('purchase_requisition_id'):
                supplierinfo.purchase_requisition_id.sudo().write({
                    'date_start': supplierinfo.date_start,
                    'date_end': supplierinfo.date_end,
                })
        return res

    def _is_exhausted_blanket_order(self):
        self.ensure_one()
        if not self.purchase_requisition_line_id:
            return False
        precision = self.env['decimal.precision'].precision_get('Product Unit')
        return float_compare(self.purchase_requisition_line_id.remaining_qty, 0.0, precision_digits=precision) <= 0


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _prepare_sellers(self, params=False):
        sellers = super(ProductProduct, self)._prepare_sellers(params=params)
        if params and params.get('order_id') and params['order_id']._fields.get("requisition_ids"):
            return sellers.filtered(lambda s: not s.purchase_requisition_id or s.purchase_requisition_id in params['order_id'].requisition_ids._origin)
        else:
            return sellers

    def _get_filtered_sellers(self, partner_id=False, quantity=0.0, date=None, uom_id=False, params=False):
        sellers = super()._get_filtered_sellers(partner_id=partner_id, quantity=quantity, date=date, uom_id=uom_id, params=params)
        if self.env.context.get('exclude_blanket_orders'):
            return sellers.filtered(lambda s: not s.purchase_requisition_line_id)
        if self.env.context.get('include_exhausted_blanket_orders'):
            return sellers
        return sellers.filtered(lambda s: not s._is_exhausted_blanket_order())

    def _select_seller(self, partner_id=False, quantity=0.0, date=None, uom_id=False, ordered_by='price_discounted', params=False):
        sellers = self._get_filtered_sellers(partner_id=partner_id, quantity=quantity, date=date, uom_id=uom_id, params=params)
        blanket_order_seller = sellers.filtered('purchase_requisition_line_id')[:1]
        if blanket_order_seller:
            return blanket_order_seller._get_seller_info()

        seller_info = super()._select_seller(partner_id=partner_id, quantity=quantity, date=date, uom_id=uom_id, ordered_by=ordered_by, params=params)
        if seller_info or self.env.context.get('include_exhausted_blanket_orders') \
                or self.env.context.get('skip_exhausted_blanket_order_fallback'):
            return seller_info

        exhausted_seller = self.with_context(include_exhausted_blanket_orders=True)._get_filtered_sellers(
            partner_id=partner_id, quantity=quantity, date=date, uom_id=uom_id, params=params,
        ).filtered('purchase_requisition_line_id')[:1]
        if not exhausted_seller:
            return seller_info
        return {
            **exhausted_seller._get_seller_info(),
            'price': 0.0,
            'price_discounted': 0.0,
        }
