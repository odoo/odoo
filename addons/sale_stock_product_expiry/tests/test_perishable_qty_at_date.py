from freezegun import freeze_time
from odoo import Command
from odoo.addons.stock.tests.common import TestStockCommon
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestPerishableQtyAtDate(TestStockCommon, HttpCase):

    @freeze_time("2025-10-01")
    def test_forecast_widget_perishable_qty_at_date(self):
        product_exp = self.env['product.product'].create([{
            'name': f'Perishable Product {i}',
            'is_storable': True,
            'tracking': 'lot',
            'use_expiration_date': True,
            'expiration_time': 7,
            'removal_time': 1,
            'use_time': 2,
            'alert_time': 3,
            'sale_delay': i * 5,
        } for i in (1, 2)])

        partner = self.env['res.partner'].create({'name': 'Buyer'})

        # Create 3 lots with different expiration dates for each product_exp
        lot_records = self.env['stock.lot'].create([{
            'name': f'LOT{i:03d}',
            'product_id': p.id,
            'expiration_date': f'2025-10-{i * 5:02d}',
        } for p in product_exp for i in range(1, 4)])

        # Add stock to each lot
        for lot in lot_records:
            self.env['stock.quant']._update_available_quantity(lot.product_id, self.stock_location, 100, lot_id=lot)

        # update customer lead time, and create SO
        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'order_line': [Command.create({
                'product_id': product_exp[i].id,
                'product_uom_qty': 50,
                'price_unit': 100,
            }) for i in range(2)],
        })
        self.assertEqual(sale_order.order_line[0].virtual_available_at_date, 200)
        self.assertEqual(sale_order.order_line[1].virtual_available_at_date, 100)
        url = f"odoo/sales/{sale_order.id}"
        self.start_tour(url, 'test_forecast_widget_perishable_qty_at_date', login='admin')
