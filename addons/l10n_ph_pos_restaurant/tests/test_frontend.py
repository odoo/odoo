# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPosDiscountPrivilegesFrontend(TestPointOfSaleHttpCommon):
    """
    End-to-end coverage of the Discount Privileges wizard through the actual
    POS UI: OWL rendering, RPC round-trip, and the frontend's related_models
    schema registration are only exercised by a real client, never by a
    TransactionCase.
    """

    @classmethod
    @AccountTestInvoicingCommon.setup_country("ph")
    def setUpClass(cls):
        super().setUpClass()

        ChartTemplate = cls.env["account.chart.template"].with_company(cls.env.company)
        tax_sale_12 = ChartTemplate.ref("l10n_ph_tax_sale_12")
        fpos_sc_pwd = ChartTemplate.ref("l10n_ph_fiscal_position_discount_privileges")

        cls.env["l10n_ph.discount.privilege"].create(
            [
                {
                    "name": "Senior Citizen",
                    "discount_type": "sc",
                    "discount_amount": 0.2,
                    "fiscal_position_id": fpos_sc_pwd.id,
                    "account_id": cls.company_data["default_account_revenue"].id,
                },
                {
                    "name": "PWD",
                    "discount_type": "pwd",
                    "discount_amount": 0.2,
                    "fiscal_position_id": fpos_sc_pwd.id,
                    "account_id": cls.company_data["default_account_revenue"].id,
                },
            ],
        )
        cls.env["product.template"].create(
            {
                "name": "Test Soda",
                "available_in_pos": True,
                "list_price": 100.0,
                "taxes_id": [(6, 0, tax_sale_12.ids)],
            },
        )

    def test_discount_privileges_tour(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("l10n_ph_pos_restaurant_discount_privileges")

        sc_holder = self.env["l10n_ph.pos.discount.privilege.holder"].search(
            [("id_number", "=", "SC-REG-001")],
        )
        pwd_holder = self.env["l10n_ph.pos.discount.privilege.holder"].search(
            [("id_number", "=", "PWD-REG-001")],
        )
        self.assertEqual(len(sc_holder), 1)
        self.assertEqual(len(pwd_holder), 1)
        order = sc_holder.order_id
        self.assertEqual(pwd_holder.order_id, order)
        self.assertEqual(order.state, "paid")
        self.assertEqual(len(order.lines), 3, "regular share + SC share + PWD share")
        self.assertAlmostEqual(sum(order.lines.mapped("qty")), 3.0, places=6)
        privileged_holders = order.lines.filtered("l10n_ph_discount_privilege_id").l10n_ph_discount_privilege_holder_id
        self.assertEqual(set(privileged_holders.ids), set((sc_holder + pwd_holder).ids))
