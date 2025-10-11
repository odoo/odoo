from freezegun import freeze_time
from odoo.tests import HttpCase

class TestPerishableQtyAtDate(HttpCase):

    @freeze_time("2025-10-01")
    def test_forecast_widget_free_stock(self):
        product_exp = self.env['product.product'].create({
            'name': 'Perishable Product',
            'is_storable': True,
            'tracking': 'lot',
            'use_expiration_date': True,
            'expiration_time': 7,
            'removal_time': 1,
            'use_time': 2,
            'alert_time': 3,
        })

        # Create 3 lots with different expiration dates
        lot1 = self.env['stock.lot'].create({
            'name': 'LOT001',
            'product_id': product_exp.id,
            'expiration_date': '2025-10-05',
        })
        lot2 = self.env['stock.lot'].create({
            'name': 'LOT002',
            'product_id': product_exp.id,
            'expiration_date': '2025-10-10',
        })
        lot3 = self.env['stock.lot'].create({
            'name': 'LOT003',
            'product_id': product_exp.id,
            'expiration_date': '2025-10-15',
        })
        stock_location = self.env.ref('stock.stock_location_stock')

        self.env['stock.quant']._update_available_quantity(product_exp, stock_location, 100, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(product_exp, stock_location, 100, lot_id=lot2)
        self.env['stock.quant']._update_available_quantity(product_exp, stock_location, 100, lot_id=lot3)

        # update customer lead time, and create SO
        product_exp.sale_delay = 5
        sale_order = self.env['sale.order'].create({
            'partner_id': self.env.ref('base.res_partner_2').id,
            'order_line': [(0, 0, {
                'product_id': product_exp.id,
                'product_uom_qty': 50,
                'price_unit': 100,
            })],
        })
        self.assertEqual(sale_order.order_line.virtual_available_at_date, 200)
        url = f"odoo/sales/{sale_order.id}"
        self.start_tour(url, 'test_perishable_qty_at_date', login='admin')

        product_exp.sale_delay = 10
        sale_order = self.env['sale.order'].create({
            'partner_id': self.env.ref('base.res_partner_2').id,
            'order_line': [(0, 0, {
                'product_id': product_exp.id,
                'product_uom_qty': 50,
                'price_unit': 100,
            })],
        })
        self.assertEqual(sale_order.order_line.virtual_available_at_date, 100)
        url = f"odoo/sales/{sale_order.id}"
        self.start_tour(url, 'test_perishable_qty_at_date', login='admin')
