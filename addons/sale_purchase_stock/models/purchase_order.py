# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, api, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.depends('order_line.move_dest_ids.group_id.sale_id', 'order_line.move_ids.move_dest_ids.group_id.sale_id')
    def _compute_sale_order_count(self):
        super()._compute_sale_order_count()

    def _get_sale_orders(self):
        linked_so = self.order_line.move_dest_ids.group_id.sale_id \
                  | self.env['stock.move'].browse(self.order_line.move_ids._rollup_move_dests()).group_id.sale_id
        group_so = self.order_line.group_id.sale_id

        return super()._get_sale_orders() | linked_so | group_so


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_stock_moves(self, picking):
        res = super()._prepare_stock_moves(picking)
        for re in res:
            re['sale_line_id'] = self.sale_line_id.id
            if self.sale_line_id.route_id:
               re['route_ids'] = [Command.link(self.sale_line_id.route_id.id)]
            if self.order_id.dest_address_id:
                # In a dropshipping context we do not need the description of the purchase order or it will be displayed
                # in Delivery slip report and it may be confusing for the customer to see several times the same text (product name + description_picking).
                product = self.product_id.with_context(lang=self.order_id.dest_address_id.lang or self.env.user.lang)
                re['description_picking'] = product._get_description(
                    self.env['stock.picking.type'].browse(re['picking_type_id'])
                )
        return res

    def _get_sale_order_line_product(self):
        return self.sale_line_id.product_id

    def _find_candidate(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        # if this is defined, this is a dropshipping line, so no
        # this is to correctly map delivered quantities to the so lines
        lines = self.filtered(lambda po_line: po_line.sale_line_id.id == values['sale_line_id']) if values.get('sale_line_id') else self
        # Match candidates on the vendor-language description (rebuilt below).
        values = self._vendor_lang_procurement_values(values, lines.mapped('order_id.partner_id')[:1])
        return super(PurchaseOrderLine, lines)._find_candidate(product_id, product_qty, product_uom, location_id, name, origin, company_id, values)

    @api.model
    def _prepare_purchase_order_line_from_procurement(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, po):
        values = self._vendor_lang_procurement_values(values, po.partner_id)
        res = super()._prepare_purchase_order_line_from_procurement(product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, po)
        res['sale_line_id'] = values.get('sale_line_id', False)
        if values.get('analytic_distribution'):
            res['analytic_distribution'] = values['analytic_distribution']
        return res

    @api.model
    def _vendor_lang_procurement_values(self, values, vendor):
        """Re-render ``product_description_variants`` in the vendor's language.

        On a dropship it is pre-rendered in the customer's language by
        ``sale_stock``; regenerate it from the sale order line so the whole PO
        line name uses the vendor's language, preserving custom free-text
        values. Returns ``values`` unchanged when there is no sale line.
        """
        sale_line = self.env['sale.order.line'].browse(values.get('sale_line_id'))
        if sale_line.exists() and values.get('product_description_variants') and vendor and vendor.lang:
            values = dict(values)
            values['product_description_variants'] = sale_line.with_context(
                lang=vendor.lang,
            )._get_sale_order_line_multiline_description_variants()
        return values
