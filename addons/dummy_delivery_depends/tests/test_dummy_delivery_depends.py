from openerp.addons.stock_dummy_test.tests import test_dummy_stock_test


class TestDummyStockWithDelivery(test_dummy_stock_test.TestDummyStockTest):

    def test_01_normal_moves_dummy_stock_test(self):
        move = self.create_move(self.stock.id, self.customer.id, 4)
        move.action_done()
