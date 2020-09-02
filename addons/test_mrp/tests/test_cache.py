# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mrp.tests.common import TestMrpCommon

class TestCache(TestMrpCommon):

    def create_product_to_manufacture(self, env, name):
        product = env['product.product'].create({
            'name': name,
            'type': 'product',
            'route_ids': [
                (6, 0, [\
                    self.env.ref('stock.route_warehouse0_mto').id,
                    self.env.ref('mrp.route_warehouse0_manufacture').id],)],
        })

        bom = env['mrp.bom'].create({
            'product_id': product.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [],
        })

        return product, bom

    def create_nested_mo(self, env, swap_primary_bom_lines=False):
        productPrimary, bomPrimary = \
            self.create_product_to_manufacture(env, 'productPrimary')
        productSecondary, bomSecondary = \
            self.create_product_to_manufacture(env, 'productSecondary')

        productA = self.env.ref('product.product_product_9_product_template')
        productB = self.env.ref('product.product_product_10_product_template')

        bomSecondary.write({
            'bom_line_ids': [
                (0, 0, {'product_id': productA.id, 'product_qty': 1}),
            ]})

        if swap_primary_bom_lines:
            bomPrimary.write({
                'bom_line_ids': [
                    (0, 0, {'product_id': productSecondary.id, 'product_qty': 1}),
                    (0, 0, {'product_id': productB.id, 'product_qty': 1,}),
                ]})
        else:
            bomPrimary.write({
                'bom_line_ids': [
                    (0, 0, {'product_id': productB.id, 'product_qty': 1,}),
                    (0, 0, {'product_id': productSecondary.id, 'product_qty': 1}),
                ]})

        mo = env['mrp.production'].create({
            'name': 'MO 1',
            'product_id': productPrimary.id,
            'product_uom_id': productPrimary.uom_id.id,
            'product_qty': 1,
            'bom_id': bomPrimary.id,
        })

    def test_01_create_nested_mo_with_system_env(self):
        self.create_nested_mo(self.env)

    def test_02_create_nested_mo_with_admin_env(self):
        env = self.env(user=self.browse_ref('base.user_admin'))
        self.create_nested_mo(env)

    def test_03_create_nested_mo_swap_with_system_env(self):
        self.create_nested_mo(self.env, swap_primary_bom_lines=True)

    def test_04_create_nested_mo_swap_with_admin_env(self):
        env = self.env(user=self.browse_ref('base.user_admin'))
        self.create_nested_mo(env, swap_primary_bom_lines=True)
