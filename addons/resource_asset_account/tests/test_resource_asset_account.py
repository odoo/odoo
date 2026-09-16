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
