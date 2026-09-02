from datetime import datetime, timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.l10n_jp_stock.tests.common import TestTotalAverageCostCommon
from odoo.addons.stock_account.models.res_company import ResCompany


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestTotalAverageCost(TestTotalAverageCostCommon):
    def test_runs_for_a_product_manager(self):
        manager = self.env['res.users'].create({
            'name': 'JP Product Manager',
            'login': 'jp_product_manager',
            'group_ids': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('product.group_product_manager').id,
            ])],
        })
        self._add_opening_stock()
        self._create_move(10, 200, self.today, self.supplier_loc, self.stock_loc)
        wizard = self.env['l10n_jp_stock.total.average.cost.wizard'].with_user(manager).create({
            'category_id': self.category.id,
            'date_from': self.today - timedelta(days=2),
            'date_to': self.today,
        })
        wizard.action_apply_total_average_cost()
        self.assertAlmostEqual(self.product.standard_price, (100 * 100 + 10 * 200) / 110, places=2)

    def test_opening_scoped_to_the_active_company(self):
        other_company = self.env['res.company'].create({'name': 'JP Other Co'})
        other_stock_loc = self.env['stock.warehouse'].search(
            [('company_id', '=', other_company.id)], limit=1,
        ).lot_stock_id
        self._add_opening_stock()
        self._create_move(
            500, 100, self.today - timedelta(days=10),
            self.supplier_loc, other_stock_loc, company=other_company,
        )
        self._create_move(10, 200, self.today, self.supplier_loc, self.stock_loc)
        # qty_available spans every allowed company, the moves only the active one
        wizard = self.env['l10n_jp_stock.total.average.cost.wizard'].with_context(
            allowed_company_ids=[self.env.company.id, other_company.id],
        ).create({
            'category_id': self.category.id,
            'date_from': self.today - timedelta(days=2),
            'date_to': self.today,
        })
        wizard.action_apply_total_average_cost()
        self.assertAlmostEqual(self.product.standard_price, (100 * 100 + 10 * 200) / 110, places=2)

    def test_evaluating_the_same_period_twice_is_stable(self):
        self._add_opening_stock()
        self._create_move(10, 200, self.today, self.supplier_loc, self.stock_loc)
        self._run_category_wizard()
        first_cost = self.product.standard_price
        self.assertAlmostEqual(first_cost, (100 * 100 + 10 * 200) / 110, places=2)
        action = self._run_category_wizard()
        self.assertEqual(self.product.standard_price, first_cost)
        self.assertEqual(action['params']['type'], 'info')

    def test_lot_valuated_product_refused(self):
        # valuing each lot separately is 個別法, a different elected method
        self.product.write({'tracking': 'lot', 'lot_valuated': True})
        with self.assertRaises(UserError):
            self._run_category_wizard()

    def test_period_issues_leave_at_the_evaluated_cost(self):
        self._add_opening_stock()
        self._create_move(10, 200, self.today, self.supplier_loc, self.stock_loc)
        sale = self._create_move(20, 0, self.today, self.stock_loc, self.customer_loc)
        self._run_category_wizard()
        new_cost = (100 * 100 + 10 * 200) / 110
        self.assertAlmostEqual(self.product.standard_price, new_cost, places=2)
        # the sale is not averaged in, but it must leave at what the period averaged to,
        # so the closing entry is built on that cost
        self.assertAlmostEqual(abs(sale.value), 20 * self.product.standard_price, places=2)

    def test_closed_period_refused(self):
        self._add_opening_stock()
        self._create_move(10, 200, self.today, self.supplier_loc, self.stock_loc)
        closing_date = fields.Datetime.to_datetime(self.today)
        with patch.object(
            ResCompany, '_get_last_closing_date', return_value=closing_date,
        ), self.assertRaises(UserError):
            self._run_category_wizard()

    def test_bill_price_beats_the_order_price(self):
        self.ensure_installed('purchase_stock')
        line = self._create_po_line(self.env.company.currency_id, 10, 100)
        self._add_opening_stock()
        self._create_move(10, 100, self.today, self.supplier_loc, self.stock_loc, line.id)
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': line.order_id.partner_id.id,
            'invoice_date': self.today,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 10,
                'price_unit': 150,
                'purchase_line_id': line.id,
            })],
        })
        bill.action_post()
        self._run_category_wizard()
        # the order promised 100, the posted bill says 150 (法人税法施行令 32条1項1号)
        self.assertAlmostEqual(self.product.standard_price, (100 * 100 + 10 * 150) / 110, places=2)

    def test_consigned_receipt_ignored(self):
        self._add_opening_stock()
        consigned = self._create_move(50, 200, self.today, self.supplier_loc, self.stock_loc)
        consigned.restrict_partner_id = self.env['res.partner'].create({'name': 'JP Consignor'})
        action = self._run_category_wizard()
        # core values a consignor's goods at nothing, so they are not acquisitions either
        self.assertAlmostEqual(self.product.standard_price, 100, places=2)
        self.assertEqual(action['params']['type'], 'info')

    def test_period_boundaries_follow_the_user_timezone(self):
        self._add_opening_stock()
        # 16:00 UTC is already the next day in Tokyo, 14:00 UTC is not
        self._create_move(10, 200, datetime(2026, 1, 14, 16, 0), self.supplier_loc, self.stock_loc)
        self._create_move(5, 300, datetime(2026, 1, 14, 14, 0), self.supplier_loc, self.stock_loc)
        wizard = self.env['l10n_jp_stock.total.average.cost.wizard'].with_context(tz='Asia/Tokyo').create({
            'category_id': self.category.id,
            'date_from': self.today,
            'date_to': self.today,
        })
        wizard.action_apply_total_average_cost()
        # only the first is acquired in the period; the second opened it
        self.assertAlmostEqual(self.product.standard_price, (105 * 100 + 10 * 200) / 115, places=2)

    def test_basic_calculation(self):
        self._add_opening_stock()
        self._create_move(10, 125, self.today, self.supplier_loc, self.stock_loc)
        self._create_move(25, 110, self.today, self.supplier_loc, self.stock_loc)
        self._create_move(5, 125, self.today, self.stock_loc, self.supplier_loc)
        action = self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, 102.88, places=2)
        self.assertEqual(action['params']['type'], 'success')

    def test_customer_return_period_start_ignored(self):
        self._add_opening_stock()
        sale = self._create_move(10, 110, self.today - timedelta(days=2), self.stock_loc, self.customer_loc)
        return_move = self._create_move(5, 0, self.today, self.customer_loc, self.stock_loc)
        return_move.origin_returned_move_id = sale.id
        self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, 100, places=2)

    def test_customer_return_sale_time_cost(self):
        # the sale is valued at the standard price of its date (90), so the
        # return re-enters at that sale-time cost
        self._add_opening_stock()
        self._set_standard_price(90, self.today - timedelta(days=7))
        sale = self._create_move(10, 150, self.today - timedelta(days=5), self.stock_loc, self.customer_loc)
        self._set_standard_price(100, self.today - timedelta(days=3))
        return_move = self._create_move(10, 0, self.today, self.customer_loc, self.stock_loc)
        return_move.origin_returned_move_id = sale.id
        self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, (90 * 100 + 10 * 90) / 100, places=2)

    def test_dropship_purchase_included(self):
        self._add_opening_stock()
        self._create_move(10, 125, self.today, self.supplier_loc, self.customer_loc)
        self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, 102.27, places=2)

    def test_dropship_return_current_subtracted(self):
        # the drop-ship it cancels is in the period, so the acquisition goes back out
        self._create_move(10, 10, self.today, self.supplier_loc, self.stock_loc)
        dropship = self._create_move(20, 20, self.today, self.supplier_loc, self.customer_loc)
        return_move = self._create_move(5, 0, self.today, self.customer_loc, self.supplier_loc)
        return_move.origin_returned_move_id = dropship.id
        self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, (10 * 10 + 20 * 20 - 5 * 20) / 25, places=2)

    def test_dropship_return_prior_ignored(self):
        # the drop-ship it cancels was averaged into an earlier period, so removing
        # it here would distort a pool it never entered
        dropship = self._create_move(10, 125, self.today - timedelta(days=5), self.supplier_loc, self.customer_loc)
        self._add_opening_stock()
        return_move = self._create_move(5, 0, self.today, self.customer_loc, self.supplier_loc)
        return_move.origin_returned_move_id = dropship.id
        action = self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, 100, places=2)
        self.assertEqual(action['params']['type'], 'info')

    def test_dropship_prior_ignored(self):
        self._add_opening_stock()
        self._create_move(10, 125, self.today - timedelta(days=5), self.supplier_loc, self.customer_loc)
        self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, 100, places=2)

    def test_manufacturing_consumption_ignored(self):
        # consuming a component is an issue, not a negative acquisition, and
        # 施行令28条1項1号ハ averages acquisitions only
        production_loc = self.product.property_stock_production
        self.product.standard_price = 5
        self._create_move(10, 10, self.today, self.supplier_loc, self.stock_loc)
        self._create_move(3, 0, self.today, self.stock_loc, production_loc)
        self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, (10 * 10) / 10, places=2)

    def test_manufacturing_output_counted(self):
        production_loc = self.product.property_stock_production
        self._create_move(2, 20, self.today, self.supplier_loc, self.stock_loc)
        self._create_move(1, 14, self.today, production_loc, self.stock_loc)
        self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, (2 * 20 + 14) / 3, places=2)

    def test_opening_valued_at_period_cost(self):
        self._add_opening_stock()
        self.env['product.value'].create({
            'product_id': self.product.id,
            'company_id': self.env.company.id,
            'value': 80,
            'date': fields.Datetime.to_datetime(self.today - timedelta(days=3)),
        })
        self._create_move(10, 100, self.today, self.supplier_loc, self.stock_loc)
        self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, (100 * 80 + 10 * 100) / 110, places=2)

    def test_price_history_dated_at_period_start(self):
        self._add_opening_stock()
        self._create_move(10, 200, self.today, self.supplier_loc, self.stock_loc)
        self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, (100 * 100 + 10 * 200) / 110, places=2)
        product_value = self.env['product.value'].search(
            [('product_id', '=', self.product.id), ('move_id', '=', False)],
            order='id desc', limit=1,
        )
        # the evaluated cost takes effect at the start of the period it covers, so
        # the period's own issues leave at it, not on the day the wizard was run
        self.assertEqual(
            fields.Datetime.context_timestamp(self, product_value.date).date(),
            self.today - timedelta(days=2),
        )
        self.assertEqual(product_value.value, self.product.standard_price)
        self.assertIn('Total average cost evaluation', product_value.description)

    def test_consecutive_periods_use_previous_cost(self):
        self._add_opening_stock()
        self.env['product.value'].create({
            'product_id': self.product.id,
            'company_id': self.env.company.id,
            'value': 80,
            'date': fields.Datetime.to_datetime(self.today - timedelta(days=3)),
        })
        self._create_move(10, 100, self.today, self.supplier_loc, self.stock_loc)
        self._run_category_wizard()
        first_cost = self.product.standard_price
        self.assertAlmostEqual(first_cost, (100 * 80 + 10 * 100) / 110, places=2)
        # the second period opens on the cost the first one produced; if that
        # cost were dated at the run time instead, the stale 80 would win
        self._create_move(10, 200, self.today + timedelta(days=1), self.supplier_loc, self.stock_loc)
        self._run_category_wizard(
            date_from=self.today + timedelta(days=1),
            date_to=self.today + timedelta(days=2),
        )
        self.assertAlmostEqual(self.product.standard_price, (110 * first_cost + 10 * 200) / 120, places=2)

    def test_inventory_adjustments_ignored(self):
        self._add_opening_stock()
        self._create_move(50, 120, self.today, self.supplier_loc, self.stock_loc)
        # physical count finds 20 extra units, then 10 missing
        quant = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,
            'location_id': self.stock_loc.id,
            'inventory_quantity': 170,
        })
        quant.action_apply_inventory()
        quant.inventory_quantity = 160
        quant.action_apply_inventory()
        self.env['stock.move'].search([
            ('product_id', '=', self.product.id), ('is_inventory', '=', True),
        ]).date = fields.Datetime.to_datetime(self.today)
        action = self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, (100 * 100 + 50 * 120) / 150, places=2)
        self.assertEqual(action['params']['type'], 'success')

    def test_inter_wh_transit_ignored(self):
        self.product.standard_price = 50
        # backdate the price change so it is in effect before the period
        price_value = self.env['product.value'].search(
            [('product_id', '=', self.product.id), ('move_id', '=', False)],
            order='id desc', limit=1,
        )
        price_value.date = fields.Datetime.to_datetime(self.today - timedelta(days=3))
        self._add_opening_stock()
        transit_loc = self.env['stock.location'].create({'name': 'JP Transit', 'usage': 'transit'})
        other_stock_loc = self.env['stock.location'].create({'name': 'JP Other WH', 'usage': 'internal'})
        out = self._create_move(10, 80, self.today, self.stock_loc, transit_loc)
        ret = self._create_move(10, 80, self.today, transit_loc, other_stock_loc)
        ret.move_orig_ids = [(4, out.id)]
        action = self._run_category_wizard()
        self.assertEqual(self.product.standard_price, 50)
        self.assertEqual(action['params']['type'], 'info')

    def test_manual_customer_return_counted(self):
        self._add_opening_stock()
        self._create_move(10, 90, self.today, self.customer_loc, self.stock_loc)
        self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, (100 * 100 + 10 * 90) / 110, places=2)

    def test_free_sample_receipt_at_zero(self):
        self._add_opening_stock()
        self._create_move(10, 0, self.today, self.supplier_loc, self.stock_loc)
        action = self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, (100 * 100) / 110, places=2)
        self.assertEqual(action['params']['type'], 'success')

    def test_negative_total_skipped(self):
        self._create_move(10, 100, self.today, self.supplier_loc, self.stock_loc)
        self._create_move(15, 80, self.today, self.stock_loc, self.supplier_loc)
        action = self._run_category_wizard()
        self.assertEqual(self.product.standard_price, 100)
        self.assertEqual(action['params']['type'], 'warning')

    def test_prior_supplier_return_ignored(self):
        purchase = self._create_move(10, 90, self.today - timedelta(days=5), self.supplier_loc, self.stock_loc)
        self._add_opening_stock()
        return_move = self._create_move(10, 0, self.today, self.stock_loc, self.supplier_loc)
        return_move.origin_returned_move_id = purchase.id
        self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, 100, places=2)

    def test_product_selection_scoped(self):
        other_product = self.env['product.product'].create({'name': 'JP Other Product', 'categ_id': self.category.id, 'standard_price': 50})
        self._create_move(10, 200, self.today, self.supplier_loc, self.stock_loc, product=other_product)
        self._add_opening_stock()
        self._create_move(10, 150, self.today, self.supplier_loc, self.stock_loc)
        self._run_wizard(product_ids=[self.product.id])
        self.assertAlmostEqual(self.product.standard_price, 104.55, places=2)
        self.assertEqual(other_product.standard_price, 50)

    def test_purchase_fx_at_move_date(self):
        self.ensure_installed('purchase_stock')
        foreign_currency = self.env.ref('base.EUR')
        company_currency = self.env.company.currency_id
        self.assertNotEqual(foreign_currency, company_currency)
        self.env['res.currency.rate'].create({'name': self.today - timedelta(days=1), 'rate': 2, 'currency_id': foreign_currency.id})
        self.env['res.currency.rate'].create({'name': self.today + timedelta(days=1), 'rate': 4, 'currency_id': foreign_currency.id})
        line = self._create_po_line(foreign_currency, 10, 125)
        self._create_move(10, 125, self.today + timedelta(days=2), self.supplier_loc, self.stock_loc, line.id)
        receipt_date = self.today + timedelta(days=2)
        expected_purchase_val = foreign_currency._convert(10 * 125, company_currency, self.env.company, receipt_date)
        self.assertNotAlmostEqual(expected_purchase_val, foreign_currency._convert(10 * 125, company_currency, self.env.company, self.today))
        self._add_opening_stock()
        self._run_category_wizard(date_to=receipt_date)
        self.assertAlmostEqual(self.product.standard_price, (100 * 100 + expected_purchase_val) / 110, places=2)

    def test_supplier_return_period_start(self):
        purchase = self._create_move(10, 150, self.today - timedelta(days=2), self.supplier_loc, self.stock_loc)
        self._add_opening_stock()
        return_move = self._create_move(5, 0, self.today, self.stock_loc, self.supplier_loc)
        return_move.origin_returned_move_id = purchase.id
        self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, (100 * 100 + 10 * 150 - 5 * 150) / 105, places=2)

    def test_transit_receipt_included(self):
        transit_loc = self.env['stock.location'].create({'name': 'JP Transit', 'usage': 'transit'})
        self._add_opening_stock()
        self._create_move(10, 125, self.today - timedelta(days=1), self.supplier_loc, transit_loc)
        self._create_move(10, 125, self.today, transit_loc, self.stock_loc)
        self._run_category_wizard()
        self.assertAlmostEqual(self.product.standard_price, 102.27, places=2)
