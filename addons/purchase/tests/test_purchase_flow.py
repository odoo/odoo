from odoo import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("-at_install", "post_install")
class TestPurchaseFlowTourPostInstall(AccountTestInvoicingCommon, HttpCase):
    def test_basic_purchase_flow_with_minimal_access_rights(self):
        purchase_user = self.env["res.users"].create(
            {
                "name": "Super Purchase Woman",
                "login": "SuperPurchaseWoman",
                "group_ids": [Command.set([self.ref("purchase.group_purchase_user")])],
            }
        )
        purchase_order = (
            self.env["purchase.order"]
            .with_user(purchase_user.id)
            .create(
                {
                    "partner_id": self.partner_a.id,
                    "line_ids": [
                        Command.create(
                            {
                                "name": self.product.name,
                                "product_id": self.product.id,
                                "product_qty": 1,
                            }
                        )
                    ],
                }
            )
        )
        purchase_order.action_confirm()
        self.start_tour(
            "/odoo",
            "test_basic_purchase_flow_with_minimal_access_rights",
            login="SuperPurchaseWoman",
        )


@tagged("post_install", "-at_install")
class TestPurchaseOrderLineTaxPickerUI(AccountTestInvoicingCommon, HttpCase):
    @classmethod
    def get_default_groups(cls):
        return super().get_default_groups() | cls.quick_ref(
            "purchase.group_purchase_manager"
        )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.germany = cls.env.ref("base.de")
        cls.foreign_position = cls.env["account.fiscal.position"].create(
            {
                "name": "German registration",
                "country_id": cls.germany.id,
                "foreign_vat": "DE123456788",
            }
        )
        german_group = cls.env["account.tax.group"].create(
            {
                "name": "German Taxes",
                "company_ids": [Command.set(cls.env.company.ids)],
                "country_id": cls.germany.id,
            }
        )
        cls.env["account.tax"].create(
            [
                {
                    "name": "TAXPICK DE",
                    "amount": 19.0,
                    "type_tax_use": "purchase",
                    "country_id": cls.germany.id,
                    "tax_group_id": german_group.id,
                },
                {"name": "TAXPICK HOME", "amount": 10.0, "type_tax_use": "purchase"},
            ]
        )

    def _create_order(self, fiscal_position):
        order = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "fiscal_position_id": fiscal_position.id,
                "line_ids": [
                    Command.create({"product_id": self.product_a.id, "product_qty": 1})
                ],
            }
        )
        order.line_ids.tax_ids = False
        return order

    def test_the_order_tax_country_follows_its_fiscal_position(self):
        foreign = self._create_order(self.foreign_position)
        self.assertEqual(foreign.tax_country_id, self.germany)
        self.assertEqual(foreign.line_ids.tax_country_id, self.germany)
        foreign.fiscal_position_id = False
        self.assertEqual(
            foreign.tax_country_id,
            self.env.company.account_config_id.account_fiscal_country_id,
        )

    def test_a_foreign_vat_order_offers_only_taxes_of_that_country(self):
        order = self._create_order(self.foreign_position)
        self.start_tour(
            f"/odoo/purchases/{order.id}",
            "purchase_order_line_tax_picker_foreign_vat",
            login=self.env.user.login,
        )

    def test_a_domestic_order_offers_no_foreign_country_taxes(self):
        order = self._create_order(self.env["account.fiscal.position"])
        self.assertNotEqual(order.fiscal_position_id.country_id, self.germany)
        self.start_tour(
            f"/odoo/purchases/{order.id}",
            "purchase_order_line_tax_picker_domestic",
            login=self.env.user.login,
        )
