# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain


class ProductReplenish(models.TransientModel):
    _inherit = 'product.replenish'

    partner_id = fields.Many2one('res.partner', string='Supplier')

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
            if orderpoint.route_id:
                res['route_id'] = orderpoint.route_id.id
            if orderpoint.supplier_id:
                res['partner_id'] = orderpoint.supplier_id.partner_id.id
        return res

    @api.onchange('route_id')
    def _onchange_route_id(self):
        if self.show_vendor:
            self.partner_id = self._resolve_supplier_id().partner_id
        elif not self.show_vendor:
            self.partner_id = False

    @api.depends('quantity', 'product_uom_id', 'partner_id', 'route_id')
    def _compute_date_planned(self):
        super()._compute_date_planned()
        for rec in self:
            if 'buy' in rec.route_id.rule_ids.mapped('action'):
                rec.date_planned = rec._get_date_planned(rec.route_id, supplier=rec._resolve_supplier_id(), show_vendor=rec.show_vendor)

    def _prepare_run_values(self):
        res = super()._prepare_run_values()
        if self.partner_id:
            res['procurement_partner'] = self.partner_id
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
        if 'buy' not in route_id.rule_ids.mapped('action'):
            return date

        supplier = kwargs.get('supplier')
        show_vendor = kwargs.get('show_vendor')
        if not show_vendor or not supplier:
            return date

        delay = supplier.delay + self.env.company.days_to_purchase

        return fields.Datetime.add(date, days=delay)

    def _get_route_domain(self, product_tmpl_id):
        domain = super()._get_route_domain(product_tmpl_id)
        buy_route = self.env.ref('purchase_stock.route_warehouse0_buy', raise_if_not_found=False)
        if buy_route and not product_tmpl_id.seller_ids:
            domain = Domain.AND([domain, Domain('id', '!=', buy_route.id)])
        return domain

    def _resolve_supplier_id(self):
        """ Return the seller, forcing the partner if it is set manually """
        return self.env['stock.rule']._pick_supplier(
            self.env.company,
            self.product_id,
            partner_id=self.partner_id,
            qty=self.quantity,
            uom_id=self.product_uom_id,
            params={"force_uom": True},
        )
