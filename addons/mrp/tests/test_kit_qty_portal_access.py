# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.mrp.tests.common import TestMrpCommon


@tagged('post_install', '-at_install')
class TestKitQtyPortalAccess(TestMrpCommon):

    def test_compute_kit_quantities_as_portal_user(self):
        """Kit qty fields must be readable for portal users (e.g. website shop).

        Phantom BoM qty computation needs mrp.bom and component stock. Portal/public
        users have no BOM ACL and often cannot read unpublished components, which
        previously raised AccessError on shop/portal pages for kit products.

        website_sale grants product read to portal/public (as on a real shop); this
        test mirrors that ACL without requiring the full website stack.
        """
        portal_group = self.env.ref('base.group_portal')
        public_group = self.env.ref('base.group_public')
        product_model = self.env.ref('product.model_product_product')
        template_model = self.env.ref('product.model_product_template')
        for group in (portal_group, public_group):
            self.env['ir.model.access'].search([
                ('model_id', 'in', [product_model.id, template_model.id]),
                ('group_id', '=', group.id),
            ]).unlink()
            self.env['ir.model.access'].create([
                {
                    'name': f'test product.product {group.full_name}',
                    'model_id': product_model.id,
                    'group_id': group.id,
                    'perm_read': True,
                },
                {
                    'name': f'test product.template {group.full_name}',
                    'model_id': template_model.id,
                    'group_id': group.id,
                    'perm_read': True,
                },
            ])

        component = self.env['product.product'].create({
            'name': 'Portal Kit Component',
            'type': 'product',
        })
        kit = self.env['product.product'].create({
            'name': 'Portal Phantom Kit',
            'type': 'product',
        })
        self.env['mrp.bom'].create({
            'product_tmpl_id': kit.product_tmpl_id.id,
            'product_id': kit.id,
            'type': 'phantom',
            'product_qty': 1.0,
            'bom_line_ids': [(0, 0, {
                'product_id': component.id,
                'product_qty': 2.0,
            })],
        })
        warehouse = self.env.ref('stock.warehouse0')
        self.env['stock.quant']._update_available_quantity(
            component, warehouse.lot_stock_id, 10.0,
        )

        portal_user = self.env['res.users'].create({
            'name': 'Portal Kit Qty User',
            'login': 'portal_kit_qty@example.com',
            'groups_id': [(6, 0, [portal_group.id])],
        })
        public_user = self.env.ref('base.public_user')

        for user in (portal_user, public_user):
            with self.subTest(user=user.login):
                qty_dict = kit.with_user(user)._compute_quantities_dict(
                    None, None, None,
                )
                self.assertIn(kit.id, qty_dict)
                self.assertEqual(
                    qty_dict[kit.id]['qty_available'],
                    5.0,
                    "10 components / 2 per kit should yield 5 kits available",
                )
