# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class ProductReplenish(models.TransientModel):
    _inherit = 'product.replenish'

    @api.depends('route_id', 'supplier_id')
    def _compute_date_planned(self):
        super()._compute_date_planned()
        for rec in self:
            if rec.route_id.name == 'Buy':
                rec.date_planned = rec._get_date_planned(rec.route_id, supplier=rec.supplier_id, show_supplier=rec.show_supplier)

    def _prepare_run_values(self):
        res = super()._prepare_run_values()
        if self.supplier_id:
            res['supplierinfo_id'] = self.supplier_id
            res['group_id'].partner_id = self.supplier_id.partner_id
        return res

    def action_stock_replenishment_info(self):
        self.ensure_one()
        orderpoint = self.env["stock.warehouse.orderpoint"].search([("product_id", "=", self.product_id.id), ("warehouse_id", "=", self.warehouse_id.id)], limit=1)
        if not orderpoint:
            orderpoint = self.env["stock.warehouse.orderpoint"].create({
                "product_id": self.product_id.id,
                "warehouse_id": self.warehouse_id.id,
            })
        action = orderpoint.action_stock_replenishment_info()

        action["context"] = {
            'default_orderpoint_id': orderpoint.id,
            'replenish_id': self.id,
        }
        return action

    def _get_record_to_notify(self, date):
        order_line = self.env['purchase.order.line'].search([('write_date', '>=', date)], limit=1)
        return order_line or super()._get_record_to_notify(date)

    def _get_replenishment_order_notification_link(self, order_line):
        if order_line._name == 'purchase.order.line':
            return [{
                'label': order_line.order_id.display_name,
                'url': f'/odoo/action-purchase.action_rfq_form/{order_line.order_id.id}',
            }]
        return super()._get_replenishment_order_notification_link(order_line)

    def _get_date_planned(self, route_id, **kwargs):
        date = super()._get_date_planned(route_id, **kwargs)
        if route_id.name != 'Buy':
            return date

        supplier = kwargs.get('supplier')
        show_supplier = kwargs.get('show_supplier')
        if not show_supplier or not supplier:
            return date

        delay = supplier.delay + self.env.company.days_to_purchase

        if bool(self.env['ir.config_parameter'].sudo().get_param('purchase.use_po_lead')):
            delay += self.env.company.po_lead
        return fields.Datetime.add(date, days=delay)
