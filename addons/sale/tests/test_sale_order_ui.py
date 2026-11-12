# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.product.tests.common import ProductVariantsCommon


@tagged('post_install', '-at_install')
class TestSaleOrderUI(HttpCase, ProductVariantsCommon):

    def test_sale_order_keep_uom_on_variant_wizard_quantity_change(self):
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({
                'product_id': self.product_template_sofa.product_variant_ids[0].id,
                'product_uom_id': self.uom_dozen.id,
                'product_uom_qty': 1,
            })],
        })

        self.start_tour(
            f'/odoo/sales/{so.id}',
            'sale_order_keep_uom_on_variant_wizard_quantity_change',
            login="admin",
        )

        sol = so.order_line[0]
        self.assertEqual(sol.product_uom_id, self.uom_dozen)

    def test_sale_order_ignore_previous_uom_on_product_change(self):
        optional_product = self.env['product.template'].create({'name': "Optional Product"})
        product_packed = self.env['product.product'].create({
            'name': "Packed Product",
            'uom_id': self.uom_unit.id,
            'uom_ids': [Command.set(self.uom_pack_6.ids)],
            'list_price': 10.0,
        })
        product_configurable = self.env['product.product'].create({
            'name': "Configurable Product",
            'uom_id': self.uom_unit.id,
            'list_price': 10.0,
            'optional_product_ids': [Command.set(optional_product.ids)],
        })
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({
                'product_id': product_packed.id,
                'product_uom_id': self.uom_pack_6.id,
                'product_uom_qty': 1,
            })],
        })

        self.start_tour(
            f'/odoo/sales/{so.id}',
            'sale_order_ignore_previous_uom_on_product_change',
            login="admin",
        )

        sol = so.order_line
        self.assertEqual(sol.product_id, product_configurable)
        self.assertEqual(sol.product_uom_id, self.uom_unit)
        self.assertEqual(sol.price_unit, 10.0)
