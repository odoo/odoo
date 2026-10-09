# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


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
        # Restaurant menu prices are VAT-inclusive: the privilege removes the
        # VAT from the price of the ID holder shares.
        tax_sale_12.price_include_override = "tax_included"

        cls.privilege_sc = ChartTemplate.ref("l10n_ph_discount_privilege_sc_20_vat_incl")
        cls.privilege_pwd = ChartTemplate.ref("l10n_ph_discount_privilege_pwd_20_vat_incl")
        cls.juan = cls.env["res.partner"].create(
            {
                "name": "Juan Dela Cruz",
                "country_id": cls.env.ref("base.ph").id,
                "additional_identifiers": {"PH_SC_ID": "SC-REG-001"},
            },
        )
        cls.abigail = cls.env["res.partner"].create(
            {
                "name": "Abigail Dela Cruz",
                "country_id": cls.env.ref("base.ph").id,
                "additional_identifiers": {"PH_PWD_ID": "PWD-REG-001"},
            },
        )
        cls.env["res.partner"].create({"name": "Pedro Penduko", "country_id": cls.env.ref("base.ph").id})
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
        self.start_pos_tour("l10n_ph_pos_discount_privileges")

        order = self.env["pos.order"].search([("partner_id", "=", self.juan.id)])
        self.assertEqual(order.state, "paid")
        self.assertEqual(len(order.lines), 3, "regular share + SC share + PWD share")
        self.assertAlmostEqual(sum(order.lines.mapped("qty")), 3.0, places=6)
        # 100 VAT-inclusive, i.e. 89.29 VAT-exempt minus 20% per ID holder
        # share, even after the customer was changed.
        self.assertEqual(
            sorted(order.lines.mapped("price_subtotal_incl")),
            [71.43, 71.43, 100.0],
        )
        self.assertRecordValues(order.lines.filtered("l10n_ph_discount_privilege_id").sorted("l10n_ph_holder_name"), [
            {
                "l10n_ph_discount_privilege_id": self.privilege_pwd.id,
                "l10n_ph_holder_partner_id": self.abigail.id,
                "l10n_ph_holder_name": "Abigail Dela Cruz",
                "l10n_ph_holder_id_number": "PWD-REG-001",
                "l10n_ph_holder_representative_name": "Maria Dela Cruz",
                "l10n_ph_holder_representative_id": "REP-001",
            },
            {
                "l10n_ph_discount_privilege_id": self.privilege_sc.id,
                "l10n_ph_holder_partner_id": self.juan.id,
                "l10n_ph_holder_name": "Juan Dela Cruz",
                "l10n_ph_holder_id_number": "SC-REG-001",
                "l10n_ph_holder_representative_name": False,
                "l10n_ph_holder_representative_id": False,
            },
        ])
        # The regular share remembers its remaining headcount (3 persons, 2 ID
        # holders) through the POS synchronizations that followed the split.
        regular = order.lines.filtered(lambda line: not line.l10n_ph_discount_privilege_id)
        self.assertEqual(regular.l10n_ph_persons_sharing, 1)

    def test_discount_privileges_undo_tour(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("l10n_ph_pos_discount_privileges_undo")

        order = self.env["pos.order"].search([("session_id", "=", self.main_pos_config.current_session_id.id)])
        self.assertEqual(order.state, "paid")
        self.assertRecordValues(order.lines, [{
            "qty": 2.0,
            "l10n_ph_discount_privilege_id": False,
            "l10n_ph_holder_partner_id": False,
            "l10n_ph_persons_sharing": 2,
            "price_subtotal_incl": 200.0,
        }])
