# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.osv.expression import AND


class ProductReplenish(models.TransientModel):
    _inherit = 'product.replenish'

    supplier_id = fields.Many2one("product.supplierinfo", string="Vendor")
    show_vendor = fields.Boolean(compute="_compute_show_vendor")

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if res.get('product_id'):
            product_id = self.env['product.product'].browse(res['product_id'])
            product_tmpl_id = product_id.product_tmpl_id
            company = product_tmpl_id.company_id or self.env.company
            if 'warehouse_id' not in res:
                res['warehouse_id'] = self.env['stock.warehouse'].search([
                    *self.env['stock.warehouse']._check_company_domain(company),
                ], limit=1).id
            orderpoint = self.env['stock.warehouse.orderpoint'].search([('product_id', 'in', [product_tmpl_id.product_variant_id.id, product_id.id]), ("warehouse_id", "=", res['warehouse_id'])], limit=1)
            res['supplier_id'] = False
            if orderpoint:
                res['supplier_id'] = orderpoint.supplier_id.id
            elif product_tmpl_id.seller_ids:
                res['supplier_id'] = product_tmpl_id.seller_ids[0].id
        return res

    @api.depends('route_id', 'supplier_id')
    def _compute_date_planned(self):
        super()._compute_date_planned()
        for rec in self:
            if rec.route_id.name == 'Buy':
                rec.date_planned = rec._get_date_planned(rec.route_id, supplier=rec.supplier_id, show_vendor=rec.show_vendor)

    @api.depends('route_id')
    def _compute_show_vendor(self):
        for rec in self:
            rec.show_vendor = rec._get_show_vendor(rec.route_id)

    @api.onchange('route_id')
    def _onchange_route_id(self):
        for rec in self:
            if rec.route_id == self.env.ref('purchase_stock.route_warehouse0_buy', raise_if_not_found=False) and not rec.product_id.product_tmpl_id.seller_ids:
                return {
                    'warning': {
                        'title': _("Vendor Not Found in Product %s", rec.product_id.name),
                        'message': _("Go on the product form and add the list of vendors"),
                    },
                }

    def _prepare_run_values(self):
        res = super()._prepare_run_values()
        if self.supplier_id:
            res['supplierinfo_id'] = self.supplier_id
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
            action = self.env.ref('purchase.action_rfq_form')
            return [{
                'label': order_line.order_id.display_name,
                'url': f'#action={action.id}&id={order_line.order_id.id}&model=purchase.order',
            }]
        return super()._get_replenishment_order_notification_link(order_line)

    def _get_date_planned(self, route_id, **kwargs):
        date = super()._get_date_planned(route_id, **kwargs)
        if route_id.name != 'Buy':
            return date

        supplier = kwargs.get('supplier')
        show_vendor = kwargs.get('show_vendor')
        if not show_vendor or not supplier:
            return date

        delay = supplier.delay + self.env.company.days_to_purchase

        if bool(self.env['ir.config_parameter'].sudo().get_param('purchase.use_po_lead')):
            delay += self.env.company.po_lead
        return fields.Datetime.add(date, days=delay)

    def _get_show_vendor(self, route):
        return route == self.env.ref('purchase_stock.route_warehouse0_buy', raise_if_not_found=False)

    def _get_route_domain(self, product_tmpl_id):
        domain = super()._get_route_domain(product_tmpl_id)
        if not product_tmpl_id.seller_ids:
            domain = AND([domain, [('id', '!=', self.env.ref('purchase_stock.route_warehouse0_buy', raise_if_not_found=False).id)]])
        return domain
