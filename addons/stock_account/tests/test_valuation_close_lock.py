from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.stock_account.tests.common import TestStockValuationCommon


@tagged("post_install", "-at_install")
class TestValuationCloseLock(TestStockValuationCommon):
    def _held_elsewhere(self):
        self.patch(
            self.registry["res.company"],
            "try_lock_for_update",
            lambda records, **kwargs: records.browse(),
        )

    def test_a_second_closing_is_refused_while_one_is_running(self):
        self._held_elsewhere()

        with self.assertRaises(UserError):
            self.company._close_stock_valuation()

    def test_the_button_refuses_too(self):
        self._held_elsewhere()

        with self.assertRaisesRegex(UserError, "already running"):
            self.company.action_close_stock_valuation()

    def test_the_cron_skips_a_company_being_closed_rather_than_failing(self):
        product = self.product_avco.with_company(self.company)
        self._make_in_move(product, 10, unit_cost=10)
        self.company.stock_config_id.inventory_period = "daily"
        self.company.stock_config_id.inventory_valuation = "periodic"
        self._held_elsewhere()

        self.env["res.company"]._cron_post_stock_valuation()

        self.assertFalse(
            self.env["account.move"].search(
                [
                    ("is_stock_valuation_closing", "=", True),
                    ("company_id", "=", self.company.id),
                ]
            ),
            "nothing may be booked for a company another closing holds",
        )

    def test_an_uncontended_closing_still_runs(self):
        product = self.product_avco.with_company(self.company)
        self._make_in_move(product, 10, unit_cost=10)

        self.company.action_close_stock_valuation(auto_post=True)

        self.assertTrue(
            self.env["account.move"].search(
                [
                    ("is_stock_valuation_closing", "=", True),
                    ("company_id", "=", self.company.id),
                ]
            ),
            "the lock must not stop an ordinary closing",
        )
