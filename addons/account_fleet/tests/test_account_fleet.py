from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountFleet(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids |= cls.env.ref("resource_asset.group_asset_user")
        cls.car = cls.env["resource.asset"].create(
            {
                "name": "Billed Car",
                "kind_id": cls.env.ref("resource_asset.kind_vehicle").id,
                "company_id": cls.company_data["company"].id,
            }
        )

    def test_a_vehicle_bill_is_a_vehicle_service(self):
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-01-15",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Tyres",
                            "account_id": self.company_data[
                                "default_account_expense"
                            ].id,
                            "asset_id": self.car.id,
                            "price_unit": 250.0,
                            "tax_ids": [(5, 0, 0)],
                        },
                    )
                ],
            }
        )
        bill.action_post()
        self.assertEqual(self.car.service_count, 1)
        service = self.env["resource.asset.log"].search(
            self.car.action_view_services()["domain"]
        )
        self.assertEqual((service.amount, service.state), (250.0, "done"))
