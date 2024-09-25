from odoo.addons.stock.tests.test_move import StockMove
from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestStockProductTour(StockMove, HttpCase):

    def _get_product_url(self, product_id):
        return '/odoo/action-stock.stock_product_normal_action/%s' % (product_id)

    def test_enable_product_tracking(self):
        """ Changing tracking of an existing product will raise a
            confirmation dialog if some moves are reserved
        """
        self.product.is_storable = False
        move_in = self.env['stock.move'].create({
            'name': 'test_customer',
            'location_id': self.customer_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        move_in._action_confirm()
        move_in._action_assign()

        url = self._get_product_url(self.product.id)
        self.start_tour(url, 'test_enable_product_tracking', login='admin')
        self.assertEqual(self.product.is_storable, True)
        move_in._action_cancel()

    def test_disable_product_tracking(self):
        """ Changing tracking of an existing product will raise a
            confirmation dialog if qty_available is not zero
        """
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 10)
        self.product.qty_available = 10

        url = self._get_product_url(self.product.id)
        self.start_tour(url, 'test_disable_product_tracking', login='admin')
        self.assertEqual(self.product.is_storable, False)
