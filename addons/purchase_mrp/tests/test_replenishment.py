from odoo.addons.stock.tests.common import TestStockCommon


class TestReplenishment(TestStockCommon):
    def test_effective_route(self):
        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'product_id': self.productA.id,
            'product_min_qty': 2,
            'product_max_qty': 4,
        })
        # No routes are available -> no effective route
        self.assertFalse(orderpoint.effective_route_id)

        # Create routes and corresponding BoM and supplier
        manufacture = self.env['stock.route'].create({
            'name': 'Manufacture',
            'rule_ids': [
                (0, 0, {
                    'name': 'Manufacture',
                    'location_dest_id': self.stock_location.id,
                    'action': 'manufacture',
                    'picking_type_id': self.picking_type_in.id,
                }),
            ],
        })
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.productA.product_tmpl_id.id,
            'product_qty': 1,
        })
        buy = self.env['stock.route'].create({
            'name': 'Buy',
            'rule_ids': [
                (0, 0, {
                    'name': 'Buy',
                    'location_dest_id': self.stock_location.id,
                    'action': 'buy',
                    'picking_type_id': self.picking_type_in.id,
                }),
            ],
        })
        self.env['product.supplierinfo'].create({
            'product_id': self.productA.id,
            'partner_id': self.partner_1.id,
            'min_qty': 10,
            'price': 50,
        })

        # Activate one of the routes
        self.productA.write({
            'route_ids': [(4, manufacture.id)],
        })
        self.env.invalidate_all()
        # Only Manufacture route is set
        self.assertEqual(orderpoint.effective_route_id, manufacture)
        # Manufacture is the effective route: there is an effective BoM, but no effective vendor
        self.assertEqual(orderpoint.effective_bom_id, bom)
        self.assertFalse(orderpoint.effective_vendor_id)

        self.productA.write({
            'route_ids': [(4, buy.id)],
        })
        self.env.invalidate_all()
        # Manufacture and Buy routes are set, but Manufacture is first
        self.assertEqual(orderpoint.effective_route_id, manufacture)
        # Manufacture is still the effective route
        self.assertEqual(orderpoint.effective_bom_id, bom)
        self.assertFalse(orderpoint.effective_vendor_id)

        orderpoint.route_id = buy
        self.env.invalidate_all()
        # Manufacture is the default route, but Buy was set explicitly
        self.assertEqual(orderpoint.effective_route_id, buy)
        self.assertEqual(orderpoint.route_id, buy)
        # Buy is the effective route: there is an effective vendor, but no effective BoM
        self.assertEqual(orderpoint.effective_vendor_id, self.partner_1)
        self.assertFalse(orderpoint.effective_bom_id)

        orderpoint.route_id = False

        self.productA.write({
            'route_ids': [(3, manufacture.id)],
        })
        self.env.invalidate_all()
        # Manufacture was removed, only Buy remains
        self.assertEqual(orderpoint.effective_route_id, buy)
        self.assertFalse(orderpoint.route_id)
        # Buy is still the effective route
        self.assertEqual(orderpoint.effective_vendor_id, self.partner_1)
        self.assertFalse(orderpoint.effective_bom_id)
