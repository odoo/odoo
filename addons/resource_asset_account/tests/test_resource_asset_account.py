from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestResourceAssetAccount(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids |= cls.env.ref("resource_asset.group_asset_manager")
        cls.company = cls.company_data["company"]
        cls.expense = cls.company_data["default_account_expense"]
        cls.asset = cls.env["resource.asset"].create(
            {
                "name": "Billed Truck",
                "kind_id": cls.env.ref("resource_asset.kind_tool").id,
                "company_id": cls.company.id,
            }
        )
        cls.service_category = cls.env["product.category"].create(
            {"name": "Asset services", "log_type": "service"}
        )
        cls.service = cls.env["product.product"].create(
            {"name": "Repair", "type": "service", "categ_id": cls.service_category.id}
        )

    def _bill(self, product=None, move_type="in_invoice", price=100.0):
        return self.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-01-15",
                "company_id": self.company.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "probe",
                            "product_id": product.id if product else False,
                            "account_id": self.expense.id,
                            "asset_id": self.asset.id,
                            "quantity": 1.0,
                            "price_unit": price,
                            "tax_ids": [(5, 0, 0)],
                        },
                    )
                ],
            }
        )

    def test_a_bill_line_on_an_asset_logs_its_cost(self):
        bill = self._bill(self.service)
        log = bill.invoice_line_ids.asset_log_ids
        self.assertEqual(log.asset_id, self.asset)
        self.assertEqual(
            (log.amount, log.log_type, log.source), (100.0, "service", "bill")
        )
        self.assertEqual(log.state, "new")
        bill.action_post()
        self.assertEqual(log.state, "done")
        self.assertEqual(self.asset.count_bill, 1)
        self.assertEqual(
            self.asset.action_view_bills()["domain"], [("id", "in", bill.ids)]
        )

    def test_a_refund_offsets_the_bill(self):
        self._bill(self.service)
        refund = self._bill(self.service, move_type="in_refund")
        self.assertEqual(refund.invoice_line_ids.asset_log_ids.amount, -100.0)

    def test_the_account_types_a_line_without_a_product(self):
        self.expense.asset_log_type = "service"
        log = self._bill().invoice_line_ids.asset_log_ids
        self.assertEqual(log.log_type, "service")

    def test_a_billed_log_follows_its_line(self):
        bill = self._bill(self.service)
        log = bill.invoice_line_ids.asset_log_ids
        with self.assertRaises(UserError):
            log.amount = 5
        with self.assertRaises(UserError):
            log.unlink()
        bill.invoice_line_ids.asset_id = False
        self.assertFalse(log.exists())


@tagged("post_install", "-at_install")
class TestAssetPartBillHold(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids |= cls.env.ref("resource_asset.group_asset_manager")
        cls.company = cls.company_data["company"]
        cls.expense = cls.company_data["default_account_expense"]
        cls.kind = cls.env["resource.asset.kind"].create(
            {"name": "Held Truck", "code": "held_truck"}
        )
        cls.position = cls.env["resource.asset.kind.position"].create(
            {
                "kind_id": cls.kind.id,
                "name": "Alternator",
                "code": "alternator",
                "expected_life_days": 365,
            }
        )
        cls.alternator = cls.env["product.product"].create({"name": "Alternator"})
        cls.asset = cls.env["resource.asset"].create(
            {
                "name": "Truck 30",
                "kind_id": cls.kind.id,
                "company_id": cls.company.id,
            }
        )

    def _install(self, day, **vals):
        return self.env["resource.asset.part"].create(
            {
                "asset_id": self.asset.id,
                "position_id": self.position.id,
                "product_id": self.alternator.id,
                "vendor_id": self.partner_a.id,
                "date_installed": f"2026-{day} 10:00:00",
                "removed_returned": True,
                "state": "installed",
                **vals,
            }
        )

    def _bill(self):
        return self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-03-01",
                "company_id": self.company.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.alternator.id,
                            "account_id": self.expense.id,
                            "asset_id": self.asset.id,
                            "quantity": 1.0,
                            "price_unit": 500.0,
                            "tax_ids": [(5, 0, 0)],
                        },
                    )
                ],
            }
        )

    def _clear(self, part):
        self.env["resource.asset.part.clear"].create(
            {"part_ids": [(6, 0, part.ids)], "note": "Warranty claim filed"}
        ).action_clear()

    def test_a_bill_charging_a_flagged_part_is_not_posted(self):
        self._install("01-10")
        repeat = self._install("02-20")
        bill = self._bill()

        with self.assertRaises(UserError):
            bill.action_post()

        self._clear(repeat)
        bill.action_post()
        self.assertEqual(bill.state, "posted")
        self.assertEqual(bill.invoice_line_ids.asset_part_ids, repeat)

    def test_a_bill_posted_before_the_repeat_is_held_until_cleared(self):
        self._install("01-10", vendor_id=self.partner_b.id)
        bill = self._bill()
        bill.action_post()

        repeat = self._install("02-20")

        self.assertEqual(repeat.account_move_line_id, bill.invoice_line_ids)
        self.assertEqual(bill.payment_state, "blocked")
        self.assertTrue(bill.asset_part_hold)
        with self.assertRaises(UserError):
            bill.action_toggle_block_payment()
        with self.assertRaises(UserError):
            bill.action_register_payment()

        self._clear(repeat)

        self.assertEqual(bill.payment_state, "not_paid")
        self.assertFalse(bill.asset_part_hold)

    def test_a_clean_part_leaves_its_bill_alone(self):
        part = self._install("01-10")
        bill = self._bill()
        bill.action_post()

        self.assertEqual(bill.invoice_line_ids.asset_part_ids, part)
        self.assertEqual(bill.payment_state, "not_paid")
        self.assertFalse(bill.asset_part_flagged_count)

    def test_another_vendors_bill_is_not_bound(self):
        self._install("01-10")
        self._install("02-20")
        bill = self._bill()
        bill.partner_id = self.partner_b

        bill.action_post()

        self.assertFalse(bill.invoice_line_ids.asset_part_ids)
