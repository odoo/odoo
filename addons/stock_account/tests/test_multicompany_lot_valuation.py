# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestMultiCompanyLotValuation(TransactionCase):
    """
    Test that lot.avg_cost computes correctly per company context in multi-company
    databases with FIFO costing and lot valuation enabled.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_b = cls.env['res.company'].create({
            'name': 'Company B',
            'currency_id': cls.env.ref('base.EUR').id,
        })

        cls.stock_account_product_categ = cls.env['product.category'].create({
            'name': 'Test Stock Category',
            'property_cost_method': 'fifo',
            'property_valuation': 'periodic',
        })

        cls.product_fifo_lot = cls.env['product.product'].create({
            'name': 'Product FIFO Lot Valuated',
            'is_storable': True,
            'categ_id': cls.stock_account_product_categ.id,
            'tracking': 'serial',
            'company_id': False,
            'lot_valuated': True,
        })

        cls.warehouse_b = cls.env['stock.warehouse'].search([('company_id', '=', cls.company_b.id)])
        cls.supplier_location = cls.env.ref('stock.stock_location_suppliers')

    def test_lot_avg_cost_multicompany_fifo(self):
        """Test that a shared lot's avg_cost is computed correctly per company context."""

        lot_b = self.env['stock.lot'].create({
            'name': 'LOT-B-001',
            'product_id': self.product_fifo_lot.id,
            'company_id': False,
        })

        lot_b.with_company(self.company_b).standard_price = 100.0

        move_in_b = self.env['stock.move'].with_company(self.company_b).create({
            'product_id': self.product_fifo_lot.id,
            'product_uom': self.product_fifo_lot.uom_id.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.warehouse_b.lot_stock_id.id,
            'product_uom_qty': 1.0,
            'company_id': self.company_b.id,
        })
        move_in_b._action_confirm()
        move_in_b._action_assign()
        move_in_b.move_line_ids.lot_id = lot_b
        move_in_b.move_line_ids.quantity = 1.0
        move_in_b.picked = True
        move_in_b._action_done()

        self.assertEqual(
            lot_b.with_company(self.env.company).avg_cost, 0.0,
            "avg_cost should be 0 in Company A context"
        )
        self.assertEqual(
            lot_b.with_company(self.company_b).avg_cost, 100.0,
            "avg_cost should be 100 EUR in Company B context"
        )
