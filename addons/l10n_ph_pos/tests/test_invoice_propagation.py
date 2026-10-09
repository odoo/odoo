# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.l10n_ph.tests.common import TestPhCommon
from odoo.addons.l10n_ph_pos.tests.common import make_holder_vals


@tagged("post_install_l10n", "post_install", "-at_install")
class TestPosInvoicePropagation(TestPhCommon):
    """
    Coverage of pos.order._prepare_account_move_line_data_from_base_line:
    privileged POS lines must carry their privilege onto the invoice line
    (mirrors SaleOrderLine._prepare_invoice_line), grouped into one
    line_section per ID holder plus one for the regular share.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref("point_of_sale.group_pos_manager")

        ChartTemplate = cls.env["account.chart.template"].with_company(
            cls.company_data["company"],
        )
        cls.tax_sale_12 = ChartTemplate.ref("l10n_ph_tax_sale_12")

        cls.privilege_sc = ChartTemplate.ref("l10n_ph_discount_privilege_sc_20_vat_incl")
        cls.privilege_pwd = ChartTemplate.ref("l10n_ph_discount_privilege_pwd_20_vat_incl")
        cls.pizza = cls.env["product.product"].create(
            {
                "name": "Pizza Margherita",
                "list_price": 1000.0,
                "taxes_id": [Command.set(cls.tax_sale_12.ids)],
                "property_account_income_id": cls.company_data["default_account_revenue"].id,
            },
        )
        cls.pos_config = cls.env["pos.config"].create(
            {"name": "Test Restaurant", "company_id": cls.company_data["company"].id},
        )
        cls.pos_session = cls.env["pos.session"].create(
            {"config_id": cls.pos_config.id, "user_id": cls.env.uid},
        )

    def _create_order(self, qty=2.0):
        order = self.env["pos.order"].create(
            {
                "name": "Test Order",
                "company_id": self.company_data["company"].id,
                "session_id": self.pos_session.id,
                "amount_tax": 0.0,
                "amount_total": 0.0,
                "amount_paid": 0.0,
                "amount_return": 0.0,
                "lines": [
                    Command.create(
                        {
                            "product_id": self.pizza.id,
                            "qty": qty,
                            "price_unit": self.pizza.list_price,
                            "tax_ids": [Command.set(self.tax_sale_12.ids)],
                            "price_subtotal": 0.0,
                            "price_subtotal_incl": 0.0,
                        },
                    ),
                ],
            },
        )
        order.lines._onchange_amount_line_all()
        return order

    def _holder_vals(self, privilege, name, id_number):
        return make_holder_vals(self.env, privilege, name, id_number)

    def test_no_holders_falls_through_unchanged(self):
        order = self._create_order(qty=1.0)
        entries = order._prepare_account_move_line_data(aggregate=False)
        sections = [e for e in entries if e["account.move.line"].get("display_type") == "line_section"]
        self.assertFalse(sections)

    def test_sections_grouped_by_holder_with_regular_first(self):
        order = self._create_order(qty=5.0)
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[
                self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1"),
                self._holder_vals(self.privilege_pwd, "Abigail Dela Cruz", "PWD-1"),
            ],
            num_persons_sharing=5,
        )

        entries = order._prepare_account_move_line_data(aggregate=False)
        section_names = [
            e["account.move.line"]["name"]
            for e in entries
            if e["account.move.line"].get("display_type") == "line_section"
        ]
        self.assertEqual(section_names, [
            "Regular Orders",
            "ID HOLDER Juan Dela Cruz - ID Type: Senior Citizen ID - ID#: SC-1",
            "ID HOLDER Abigail Dela Cruz - ID Type: Person with Disability ID - ID#: PWD-1",
        ])

        # Sections must precede their own group's product lines, in order.
        kinds = [e["account.move.line"].get("display_type") for e in entries]
        self.assertEqual(kinds, ["line_section", "product", "line_section", "product", "line_section", "product"])

        product_entries = [e for e in entries if e["account.move.line"].get("display_type") == "product"]
        regular_entry, sc_entry, pwd_entry = product_entries
        self.assertNotIn("l10n_ph_discount_privilege_id", regular_entry["account.move.line"])
        self.assertEqual(sc_entry["account.move.line"]["l10n_ph_discount_privilege_id"], self.privilege_sc.id)
        self.assertEqual(pwd_entry["account.move.line"]["l10n_ph_discount_privilege_id"], self.privilege_pwd.id)
        self.assertEqual(sc_entry["account.move.line"]["quantity"], 1.0)
        self.assertEqual(regular_entry["account.move.line"]["quantity"], 3.0)

    def test_general_customer_note_belongs_to_no_section(self):
        """The order's general customer note heads the invoice, ahead of all
        sections, instead of ending up in the last ID holder's section. Line
        notes stay with their line."""
        order = self._create_order(qty=2.0)
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1")],
            num_persons_sharing=2,
        )
        order.general_customer_note = "Table 5 birthday"
        order.lines.filtered("l10n_ph_discount_privilege_id").customer_note = "No onions"

        entries = order._prepare_account_move_line_data(aggregate=False)
        self.assertEqual(
            [(e["account.move.line"].get("display_type"), e["account.move.line"].get("name")) for e in entries],
            [
                ("line_note", "Table 5 birthday"),
                ("line_section", "Regular Orders"),
                ("product", self.pizza.description_sale),
                ("line_section", "ID HOLDER Juan Dela Cruz - ID Type: Senior Citizen ID - ID#: SC-1"),
                ("product", self.pizza.description_sale),
                ("line_note", "No onions"),
            ],
        )

    def test_full_invoice_creation_has_sections_and_matching_totals(self):
        """The section/privilege dict output must survive an actual
        account.move.create(), not just look right as a list of dicts
        (test_sections_grouped_by_holder_with_regular_first already covers
        the dict shape and section naming/ordering in detail)."""
        order = self._create_order(qty=5.0)
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[
                self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1"),
                self._holder_vals(self.privilege_pwd, "Abigail Dela Cruz", "PWD-1"),
            ],
            num_persons_sharing=5,
        )
        invoice_vals = order._prepare_invoice_vals()
        invoice = self.env["account.move"].sudo().create(invoice_vals)

        product_lines = invoice.invoice_line_ids.filtered(lambda line: line.display_type == "product")
        self.assertAlmostEqual(sum(product_lines.mapped("quantity")), 5.0, places=6)
        privileged_lines = product_lines.filtered("l10n_ph_discount_privilege_id")
        self.assertAlmostEqual(sum(privileged_lines.mapped("l10n_ph_special_discount_amount")), 400.0, places=2)
        self.assertRecordValues(privileged_lines.sorted("l10n_ph_holder_id_number"), [
            {"l10n_ph_holder_name": "Abigail Dela Cruz", "l10n_ph_holder_id_number": "PWD-1"},
            {"l10n_ph_holder_name": "Juan Dela Cruz", "l10n_ph_holder_id_number": "SC-1"},
        ])

    def test_same_holder_applied_twice_has_one_section(self):
        """An ID holder whose privilege is applied again later on (here on
        an item ordered after the first split) keeps a single section."""
        order = self._create_order(qty=1.0)
        holder_vals = self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1")
        order._l10n_ph_apply_discount_privileges(holders_vals=[holder_vals], num_persons_sharing=1)
        self.env["pos.order.line"].create({
            "order_id": order.id,
            "product_id": self.pizza.id,
            "qty": 1.0,
            "price_unit": self.pizza.list_price,
            "tax_ids": [Command.set(self.tax_sale_12.ids)],
            "price_subtotal": 0.0,
            "price_subtotal_incl": 0.0,
        })
        order._l10n_ph_apply_discount_privileges(holders_vals=[holder_vals], num_persons_sharing=1)
        self.assertEqual(len(order.lines), 2)

        entries = order._prepare_account_move_line_data(aggregate=False)
        kinds = [e["account.move.line"].get("display_type") for e in entries]
        self.assertEqual(kinds, ["line_section", "product", "product"])
        self.assertEqual(
            entries[0]["account.move.line"]["name"],
            "ID HOLDER Juan Dela Cruz - ID Type: Senior Citizen ID - ID#: SC-1",
        )

    def test_refund_invoice_keeps_holder_sections(self):
        order = self._create_order(qty=5.0)
        order._l10n_ph_apply_discount_privileges(
            holders_vals=[self._holder_vals(self.privilege_sc, "Juan Dela Cruz", "SC-1")],
            num_persons_sharing=5,
        )
        order.state = "paid"
        refund = order._refund()

        entries = refund._prepare_account_move_line_data(aggregate=False)
        section_names = [
            e["account.move.line"]["name"]
            for e in entries
            if e["account.move.line"].get("display_type") == "line_section"
        ]
        self.assertEqual(section_names, [
            "Regular Orders",
            "ID HOLDER Juan Dela Cruz - ID Type: Senior Citizen ID - ID#: SC-1",
        ])
        sc_entry = entries[-1]["account.move.line"]
        self.assertEqual(sc_entry["l10n_ph_discount_privilege_id"], self.privilege_sc.id)
