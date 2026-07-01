# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import closing

from odoo.tests.common import TransactionCase


class ConcurrentStockQuant(TransactionCase):

    def gather_relevant(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        quants = self.env['stock.quant']._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
        return quants.filtered(lambda q: not (q.quantity == 0 and q.reserved_quantity == 0))

    def test_concurrent_increase_available_quantity(self):
        """ Increase the available quantity when a concurrent transaction is already increasing
        the reserved quanntity for the same product.
        """
        location = self.env.ref('stock.stock_location_stock')
        quant = self.env['stock.quant'].search([('location_id', '=', location.id)], limit=1)
        product = quant.product_id
        available_quantity = self.env['stock.quant']._get_available_quantity(product, location, allow_negative=True)
        # opens a new cursor and SELECT FOR UPDATE the quant, to simulate another concurrent reserved
        # quantity increase
        with closing(self.registry.cursor()) as cr:
            cr.execute("SELECT id FROM stock_quant WHERE product_id=%s AND location_id=%s", (product.id, location.id))
            quant_id = cr.fetchone()
            cr.execute("SELECT 1 FROM stock_quant WHERE id=%s FOR UPDATE", quant_id)
            self.env['stock.quant']._update_available_quantity(product, location, 1.0)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(product, location, allow_negative=True), available_quantity + 1)
        self.assertEqual(len(self.gather_relevant(product, location, strict=True)), 2)

    def test_concurent_decrease_available_quantity(self):
        """ Decrease the available quantity when a concurrent transaction is already increasing
        the reserved quanntity for the same product.
        """
        location = self.env.ref('stock.stock_location_stock')
        quant = self.env['stock.quant'].search([('location_id', '=', location.id)], limit=1)
        product = quant.product_id
        available_quantity = self.env['stock.quant']._get_available_quantity(product, location, allow_negative=True)
        # opens a new cursor and SELECT FOR UPDATE the quant, to simulate another concurrent reserved
        # quantity increase
        with closing(self.registry.cursor()) as cr:
            cr.execute("SELECT 1 FROM stock_quant WHERE id = %s FOR UPDATE", quant.ids)
            self.env['stock.quant']._update_available_quantity(product, location, -1.0)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(product, location, allow_negative=True), available_quantity - 1)
        self.assertEqual(len(self.gather_relevant(product, location, strict=True)), 2)
