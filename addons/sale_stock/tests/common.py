# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.addons.sale.tests.common import TestSaleCommon


class TestSaleStockCommon(TestSaleCommon, ProductVariantsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse_3_steps_pull = cls.env['stock.warehouse'].create({
            'name': 'Warehouse 3 steps',
            'code': '3S',
            'delivery_steps': 'pick_pack_ship',
        })
        delivery_route_3 = cls.warehouse_3_steps_pull.delivery_route_id
        delivery_route_3.rule_ids[0].write({
            'location_dest_id': delivery_route_3.rule_ids[1].location_src_id.id,
        })
        delivery_route_3.rule_ids[1].write({'action': 'pull'})
        delivery_route_3.rule_ids[2].write({'action': 'pull'})
        cls.account_income = cls.company.income_account_id

    def _inv_adj_two_units(self, product):
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': product.id,  # tracking serial
            'inventory_quantity': 2,
            'location_id': self.stock_location.id,
        }).action_apply_inventory()

    def _so_deliver(self, product, quantity=1, price=1, picking=True, partner=None, date_order=None, currency=None):
        if partner is None:
            partner = self.owner
        vals = {
            'partner_id': partner.id,
            'warehouse_id': self.warehouse.id,
            'order_line': [Command.create({
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': quantity,
                'price_unit': price,
                'tax_ids': False,
            })],
        }
        if date_order:
            vals['date_order'] = date_order
        if currency:
            vals['currency_id'] = currency.id

        so = self.env['sale.order'].sudo().create(vals)
        so.action_confirm()
        if picking:
            so.picking_ids.move_ids.write({'quantity': quantity, 'picked': True})
            so.picking_ids.button_validate()
        return so
