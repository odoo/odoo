from datetime import timedelta
from unittest import SkipTest

from odoo import fields
from odoo.tests.common import TransactionCase


class TestTotalAverageCostCommon(TransactionCase):
    @classmethod
    def ensure_installed(cls, module_name):
        if cls.env['ir.module.module']._get(module_name).state != 'installed':
            raise SkipTest(f"Module required for the test is not installed ({module_name})")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.from_string('2026-01-15')
        cls.category = cls.env['product.category'].create({'name': 'JP Test Category', 'property_cost_method': 'standard'})
        cls.product = cls.env['product.product'].create({'name': 'JP Test Product', 'categ_id': cls.category.id, 'standard_price': 100, 'is_storable': True})
        cls.supplier_loc = cls.env.ref('stock.stock_location_suppliers')
        cls.stock_loc = cls.env.ref('stock.stock_location_stock')
        cls.customer_loc = cls.env.ref('stock.stock_location_customers')

    def _create_move(self, qty, price, date, src_loc, dest_loc, purchase_line_id=None, product=None, company=None):
        move = self.env['stock.move'].with_company(company or self.env.company).create({
            'product_id': (product or self.product).id,
            'product_uom_qty': qty,
            'location_id': src_loc.id,
            'location_dest_id': dest_loc.id,
            'price_unit': price,
            'date': date,
            # purchase_stock is not a dependency, so the field may not be there
            **({'purchase_line_id': purchase_line_id} if purchase_line_id else {}),
        })
        move._action_confirm()
        move._action_assign()
        move.picked = True
        move._action_done()
        move.date = fields.Datetime.to_datetime(date)
        return move

    def _add_opening_stock(self, qty=100, price=100, days=10):
        return self._create_move(qty, price, self.today - timedelta(days=days), self.supplier_loc, self.stock_loc)

    def _set_standard_price(self, price, date, product=None):
        """
        Change the cost with an effective date, the way the wizard does.

        A plain write stamps the history at wall-clock now, which is after every
        back-dated move a test creates, so the moves would not see the new cost.
        """
        product = product or self.product
        old_price = product.standard_price
        product.with_context(disable_auto_revaluation=True).standard_price = price
        product._change_standard_price({product: old_price}, valuation_date=fields.Datetime.to_datetime(date))

    def _create_po_line(self, currency, qty, price_unit):
        order = self.env['purchase.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'JP Foreign Supplier'}).id,
            'currency_id': currency.id,
        })
        return self.env['purchase.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'product_qty': qty,
            'price_unit': price_unit,
        })

    def _run_wizard(self, date_from=None, date_to=None, **values):
        values.setdefault('date_from', self.today - timedelta(days=2) if date_from is None else date_from)
        values.setdefault('date_to', self.today if date_to is None else date_to)
        wizard = self.env['l10n_jp_stock.total.average.cost.wizard'].create(values)
        return wizard.action_apply_total_average_cost()

    def _run_category_wizard(self, **values):
        values.setdefault('category_id', self.category.id)
        return self._run_wizard(**values)
