from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestScrapKit(TransactionCase):

    def setUp(self):
        super().setUp()

        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.scrap_location = self.env['stock.location'].search(
            [('usage', '=', 'inventory'), ('company_id', '=', self.env.company.id)],
            limit=1
        )

        # Components
        self.component_a = self.env['product.product'].create({
            'name': 'Component A',
            'is_storable': True,
        })
        self.component_b = self.env['product.product'].create({
            'name': 'Component B',
            'is_storable': True,
        })

        # Kit product
        self.kit = self.env['product.product'].create({
            'name': 'Kit Product',
            'is_storable': True,
        })

        # Phantom BOM
        self.env['mrp.bom'].create({
            'product_tmpl_id': self.kit.product_tmpl_id.id,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': self.component_a.id, 'product_qty': 1}),
                (0, 0, {'product_id': self.component_b.id, 'product_qty': 1}),
            ],
        })

        # Put Minimal stock for component's (1 is enough)
        self.env['stock.quant']._update_available_quantity(
            self.component_a, self.stock_location, 1
        )
        self.env['stock.quant']._update_available_quantity(
            self.component_b, self.stock_location, 1
        )

    def test_scrap_kit_does_not_crash(self):
        scrap = self.env['stock.scrap'].create({
            'product_id': self.kit.id,
            'scrap_qty': 1,
            'location_id': self.stock_location.id,
            'scrap_location_id': self.scrap_location.id,
        })
        scrap.action_validate()
        self.assertEqual(scrap.state, 'done')
