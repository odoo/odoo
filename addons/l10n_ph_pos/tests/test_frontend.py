# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.l10n_ph_pos.tests.common import TestPosDiscountPrivilegeHttpCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPosDiscountPrivilegesFrontend(TestPosDiscountPrivilegeHttpCommon):
    """
    End-to-end coverage of the Discount Privileges wizard through the actual
    POS UI: OWL rendering, RPC round-trip, and the frontend's related_models
    schema registration are only exercised by a real client, never by a
    TransactionCase.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Restaurant menu prices are VAT-inclusive: the privilege removes the
        # VAT from the price of the ID holder shares.
        cls.tax_sale_12.price_include_override = "tax_included"
        cls.abigail = cls.env["res.partner"].create(
            {
                "name": "Abigail Dela Cruz",
                "country_id": cls.env.ref("base.ph").id,
                "additional_identifiers": {"PH_PWD_ID": "PWD-REG-001"},
            },
        )
        cls.env["res.partner"].create({"name": "Pedro Penduko", "country_id": cls.env.ref("base.ph").id})

    def test_discount_privileges_tour(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("l10n_ph_pos_discount_privileges")

        order = self.env["pos.order"].search([("partner_id", "=", self.juan.id)])
        self.assertEqual(order.state, "paid")
        # Regular share + PWD share + SC share. 100 VAT-inclusive is 89.29
        # VAT-exempt, minus 20% for each ID holder share, even after the
        # customer was changed. The regular share remembers its remaining
        # headcount (3 persons, 2 ID holders) through the POS synchronizations
        # that followed the split.
        self.assertRecordValues(
            order.lines.sorted(lambda line: (bool(line.l10n_ph_discount_privilege_id), line.l10n_ph_holder_name or "")),
            [
                {
                    "qty": 1.0,
                    "price_subtotal_incl": 100.0,
                    "l10n_ph_persons_sharing": 1,
                    "l10n_ph_discount_privilege_id": False,
                    "l10n_ph_holder_partner_id": False,
                    "l10n_ph_holder_name": False,
                    "l10n_ph_holder_id_number": False,
                    "l10n_ph_holder_representative_name": False,
                    "l10n_ph_holder_representative_id": False,
                },
                {
                    "qty": 1.0,
                    "price_subtotal_incl": 71.43,
                    "l10n_ph_persons_sharing": 0,
                    "l10n_ph_discount_privilege_id": self.privilege_pwd.id,
                    "l10n_ph_holder_partner_id": self.abigail.id,
                    "l10n_ph_holder_name": "Abigail Dela Cruz",
                    "l10n_ph_holder_id_number": "PWD-REG-001",
                    "l10n_ph_holder_representative_name": "Maria Dela Cruz",
                    "l10n_ph_holder_representative_id": "REP-001",
                },
                {
                    "qty": 1.0,
                    "price_subtotal_incl": 71.43,
                    "l10n_ph_persons_sharing": 0,
                    "l10n_ph_discount_privilege_id": self.privilege_sc.id,
                    "l10n_ph_holder_partner_id": self.juan.id,
                    "l10n_ph_holder_name": "Juan Dela Cruz",
                    "l10n_ph_holder_id_number": "SC-REG-001",
                    "l10n_ph_holder_representative_name": False,
                    "l10n_ph_holder_representative_id": False,
                },
            ],
        )

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

    def test_discount_privileges_offline_tour(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("l10n_ph_pos_discount_privileges_offline")

        orders = self.env["pos.order"].search([("session_id", "=", self.main_pos_config.current_session_id.id)])
        self.assertEqual(len(orders), 4)
        self.assertEqual(orders.mapped("amount_paid"), orders.mapped("amount_total"))

        # Completed and invoiced offline: synced as split, privileged and invoiced.
        invoiced = orders.filtered("to_invoice")
        regular = invoiced.lines.filtered(lambda line: not line.l10n_ph_discount_privilege_id)
        self.assertRecordValues(regular, [{"qty": 2.0, "price_subtotal_incl": 200.0}])
        self.assertRecordValues(invoiced.lines - regular, [{
            "qty": 1.0,
            "discount": 20.0,
            "price_subtotal_incl": 71.43,
            "l10n_ph_discount_privilege_id": self.privilege_sc.id,
            "l10n_ph_holder_partner_id": self.juan.id,
            "l10n_ph_holder_id_number": "SC-REG-001",
            "l10n_ph_split_origin_line_id": regular.id,
        }])
        self.assertEqual(
            invoiced.account_move.invoice_line_ids.filtered(lambda line: line.display_type == "line_section").mapped("name"),
            ["Regular Orders", "ID HOLDER Juan Dela Cruz - ID Type: Senior Citizen ID - ID#: SC-REG-001"],
        )

        # Refunded offline: the refund line is privileged like the refunded one
        # (refund line amounts are positive, the order is_refund).
        refund = orders.filtered("is_refund")
        self.assertRecordValues(refund.lines, [{
            "qty": -1.0,
            "discount": 20.0,
            "price_subtotal_incl": 71.43,
            "l10n_ph_discount_privilege_id": self.privilege_sc.id,
            "l10n_ph_holder_partner_id": self.juan.id,
        }])
        self.assertAlmostEqual(refund.amount_total, -71.43, places=2)
