from freezegun import freeze_time

from odoo.addons.purchase_stock.tests.test_anglo_saxon_valuation_reconciliation import TestValuationReconciliation
from odoo.tests import Form, tagged
from odoo import Command, fields


@tagged('post_install', '-at_install')
class TestPruchasePrice(TestValuationReconciliation):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids |= cls.env.ref('sales_team.group_sale_salesman')

    def test_tax_recomputation_after_creating_price_difference_lines(self):
        """ We need to make sure that the creation of price diff lines doesn't recompute the value
        of the tax after it has been manually changed
        """
        test_product = self.test_product_delivery
        test_product.categ_id.write({"property_cost_method": "average"})
        test_product.write({'standard_price': 5.0})
        date = '2026-04-21'

        # Create purchase order with a price of 5 and receive quantity
        purchase_order = self._create_purchase(test_product, date, set_tax=True, quantity=1, price_unit=5)
        with freeze_time(date):
            self._process_pickings(purchase_order.picking_ids)

        # Create sale order with a price of 5 and deliver quantity
        sale_order = self._create_sale_order_one_line(price_unit=5, product_id=test_product, product_uom_qty=1.0)
        with freeze_time(date):
            self._process_pickings(sale_order.picking_ids)

        # Create bill for PO
        bill = self._create_invoice_for_po(purchase_order, date)
        with Form(bill) as move_form:
            move_form.invoice_date = fields.Date.from_string(date)
            move_form.date = fields.Date.from_string(date)

        # Set the price as 6 to create price diff lines for 1
        bill.invoice_line_ids.write({
            "price_unit": 6
        })

        # Manually change the total tax value
        tax_line = bill.line_ids.filtered('tax_line_id')
        bill.line_ids = [Command.update(tax_line.id, {'amount_currency': 1})]

        bill.action_post()

        self.assertEqual(tax_line.amount_currency, 1.0)
