from odoo.addons.mrp.tests.common import TestMrpCommon


class TestScrapKit(TestMrpCommon):

    def test_scrap_kit_does_not_crash(self):
        self.env['stock.quant']._update_available_quantity(
            self.product_3, self.stock_location, 3
        )
        self.env['stock.quant']._update_available_quantity(
            self.product_4, self.stock_location, 2
        )
        scrap = self.env['stock.scrap'].create({
            'product_id': self.product_5.id,
            'scrap_qty': 1,
            'location_id': self.stock_location.id,
            'scrap_location_id': self.scrap_location.id,
        })
        scrap.action_validate()
        self.assertEqual(scrap.state, 'done')
