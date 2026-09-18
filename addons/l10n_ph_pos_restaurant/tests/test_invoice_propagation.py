# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.l10n_ph.tests.common import TestPhCommon


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
        cls.fpos_sc_pwd = ChartTemplate.ref("l10n_ph_fiscal_position_discount_privileges")

        cls.discount_account = cls.company_data["default_account_revenue"].copy(
            {"name": "Discount Privilege Account"},
        )
        cls.privilege_sc = cls.env["l10n_ph.discount.privilege"].sudo().create(
            {
                "name": "Senior Citizen",
                "discount_type": "sc",
                "discount_amount": 0.2,
                "fiscal_position_id": cls.fpos_sc_pwd.id,
                "account_id": cls.discount_account.id,
            },
        )
        cls.privilege_pwd = cls.env["l10n_ph.discount.privilege"].sudo().create(
            {
                "name": "PWD",
                "discount_type": "pwd",
                "discount_amount": 0.2,
                "fiscal_position_id": cls.fpos_sc_pwd.id,
                "account_id": cls.discount_account.id,
            },
        )
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
        return {"privilege_id": privilege.id, "name": name, "id_number": id_number}

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
        self.assertEqual(len(section_names), 3, "regular + 2 holders")
        self.assertEqual(section_names[0], "Regular orders")
        self.assertIn("Juan Dela Cruz", section_names[1])
        self.assertIn("Senior Citizen", section_names[1])
        self.assertIn("SC-1", section_names[1])
        self.assertIn("Abigail Dela Cruz", section_names[2])
        self.assertIn("PWD", section_names[2])
        self.assertIn("PWD-1", section_names[2])

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
