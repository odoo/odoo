# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import Command, fields
from odoo.addons.stock_account.tests.common import TestStockValuationCommon
from odoo import tools


class PurchaseTestCommon(TestStockValuationCommon):

    def _create_bill(self, product=None, quantity=None, price_unit=None, post=True, **kwargs):
        if 'purchase_order' not in kwargs:
            return super()._create_bill(product=product, quantity=quantity, price_unit=price_unit, **kwargs)
        po = kwargs.pop('purchase_order')
        bill = self.env['account.move'].browse(po.action_create_invoice()['res_id'])
        bill.invoice_date = fields.Date.today()
        if quantity:
            bill.invoice_line_ids.quantity = quantity
        if price_unit:
            bill.invoice_line_ids.price_unit = price_unit
        if post:
            bill.action_post()
        return bill

    def _receive(self, purchase_order, quantity=None):
        pickings = purchase_order.picking_ids.filtered(lambda p: p.state != 'done')
        if quantity:
            pickings.move_ids.quantity = quantity
        pickings.with_context(skip_backorder=True).button_validate()
        return pickings.move_ids

    def _create_purchase(self, product, quantity=1.0, price_unit=100.0, confirm=True, **kwargs):
        po = self.env['purchase.order'].create({
            'partner_id': kwargs['partner_id'] if kwargs.get('partner_id') else self.vendor.id,
            'currency_id': kwargs.get('currency_id') or self.company.currency_id.id,
            'order_line': [
                (0, 0, {
                    'product_id': product.id,
                    'product_qty': quantity,
                    'product_uom_id': kwargs.get('uom', product.uom_id).id,
                    'price_unit': price_unit,
                    'tax_ids': kwargs.get('tax_ids', [Command.clear()]),
                })],
        })
        if confirm:
            po.button_confirm()
        if kwargs.get('receive'):
            self._receive(po)
        return po

    def _use_route_buy(self, product, create_seller=True):
        product.route_ids = [(4, self.route_buy.id)]
        if not product.seller_ids and create_seller:
            self.env['product.supplierinfo'].create({
                'partner_id': self.vendor.id,
                'product_tmpl_id': product.product_tmpl_id.id,
            })

    # TODO: move to stock common
    def _make_procurement(self, product, product_qty, date_planned=False, procurement_values=None):
        if not procurement_values:
            procurement_values = {}
        values = {
            **procurement_values,
            'warehouse_id': self.warehouse,
            'action': 'pull_push',
            'date_planned': date_planned or fields.Datetime.to_string(fields.Datetime.now() + timedelta(days=10))  # 10 days added to current date of procurement to get future schedule date and order date of purchase order.
        }
        return self.env['stock.rule'].run([self.env['stock.rule'].Procurement(
            product, product_qty, self.uom, self.stock_location,
            product.name, '/', self.env.company, values)
        ])

    # TODO: move to purchase common
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.purchase_user = cls._create_new_internal_user(name='Purchase User', login='purchase_user', groups='purchase.group_purchase_user')
        cls.route_buy = cls.warehouse.buy_pull_id.route_id

