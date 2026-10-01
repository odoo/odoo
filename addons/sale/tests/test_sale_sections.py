from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged("post_install", "-at_install")
class TestSaleSections(SaleCommon):
    _test_user_groups = (
        'product.group_product_manager',
        'sales_team.group_sale_manager',  # FIXME: use sales_team.group_sale_salesman
    )

    _test_user_name = 'Test Sales & Product Manager'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tax_1 = cls.env["account.tax"].create({"name": "Tax 1", "amount": 10})
        cls.tax_2 = cls.env["account.tax"].create({"name": "Tax 2", "amount": 20})
        cls.sections_sale_order = cls.env["sale.order"].create({
            "partner_id": cls.partner.id,
            "order_line": [
                Command.create({"name": "r1", "product_id": cls.product.id, "price_unit": 10}),
                Command.create({"name": "Sec1", "display_type": "line_section"}),
                Command.create({
                    "name": "Sec1-r1",
                    "product_id": cls.product.id,
                    "tax_ids": cls.tax_2.ids,
                    "price_unit": 200,
                }),
                Command.create({
                    "name": "Sec1-Sub1",
                    "display_type": "line_subsection",
                    "collapse_composition": True,
                }),
                Command.create({
                    "name": "Sec1-Sub1-r1",
                    "product_id": cls.product.id,
                    "tax_ids": (cls.tax_1 + cls.tax_2).ids,
                    "price_unit": 300,
                }),
                Command.create({
                    "name": "Sec1-Sub1-r2",
                    "product_id": cls.product.id,
                    "tax_ids": (cls.tax_1 + cls.tax_2).ids,
                    "price_unit": 300,
                }),
                Command.create({
                    "name": "Sec1-Sub1-r3",
                    "product_id": cls.product.id,
                    "tax_ids": cls.tax_1.ids,
                    "price_unit": 100,
                }),
                Command.create({
                    "name": "Sec1-Sub2",
                    "display_type": "line_subsection",
                    "collapse_composition": True,
                }),
                Command.create({
                    "name": "Sec1-Sub2-r1",
                    "product_id": cls.product.id,
                    "tax_ids": cls.tax_2.ids,
                    "price_unit": 200,
                }),
                Command.create({
                    "name": "Sec1-Sub2-r2",
                    "product_id": cls.product.id,
                    "tax_ids": cls.tax_1.ids,
                    "price_unit": 100,
                }),
            ],
        })

    def test_sale_order_line_parent_id(self):
        """Ensure correct assignment of `parent_id`.

        - Lines with no preceding section/subsection → no parent.
        - Section's children (lines + subsections) → parent is the section.
        - Subsection's children → parent is the subsection.
        """
        self.assertFalse(self.sections_sale_order.order_line[0].parent_id)
        self.assertEqual(
            self.sections_sale_order.order_line[2].parent_id, self.sections_sale_order.order_line[1]
        )
        self.assertEqual(
            self.sections_sale_order.order_line[3].parent_id, self.sections_sale_order.order_line[1]
        )
        self.assertEqual(
            self.sections_sale_order.order_line[4].parent_id, self.sections_sale_order.order_line[3]
        )

    def test_sale_order_report_line_visibility_and_grouping(self):
        """Check report utils for sections.

        - `_get_order_lines_to_report` must exclude children of collapsed sections/subsections,
        but keep regular lines and headers in order.
        - `_get_grouped_section_summary` must correctly aggregate totals by tax.
        """
        lines_to_report = self.sections_sale_order._get_order_lines_to_report()
        self.assertEqual(len(lines_to_report), 5)
        self.assertEqual(
            lines_to_report.mapped("name"),
            ["r1", "Sec1", "Sec1-r1", "Sec1-Sub1", "Sec1-Sub2"],
            "Lines of hidden subsection shouldn't be visible in report",
        )

        subsection_summary_lines = lines_to_report[3]._get_grouped_section_summary()
        self.assertEqual(len(subsection_summary_lines), 2)

        self.assertEqual(subsection_summary_lines[0]["price_subtotal"], 600.00)
        self.assertEqual(subsection_summary_lines[1]["price_subtotal"], 100.00)

    def test_sale_order_report_line_visibility_and_grouping_with_combo(self):
        """
        Verify that collapsed sections correctly aggregate on tax groups without splitting lines
        for untaxed zero-price items such as combo items.
        """
        product_a = self._create_product(name="Beefy burger")
        product_b = self._create_product(name="Belgian fries")
        combos = self.env["product.combo"].create([
            {"name": "Burger", "combo_item_ids": [Command.create({"product_id": product_a.id})]},
            {"name": "Side", "combo_item_ids": [Command.create({"product_id": product_b.id})]},
        ])
        product_combo = self._create_product(
            name="Meal Menu", list_price=10.0, type="combo", combo_ids=[Command.set(combos.ids)]
        )
        self.sections_sale_order.order_line = [
            Command.clear(),
            Command.create({
                "name": "Sec1",
                "display_type": "line_section",
                "collapse_composition": True,
            }),
            Command.create({"product_id": product_combo.id}),
        ]
        combo_line = self.sections_sale_order.order_line[1]
        self.sections_sale_order.order_line = [
            Command.create({
                "product_id": product_a.id,
                "combo_item_id": combos[0].combo_item_ids.id,
                "linked_line_id": combo_line.id,
            }),
            Command.create({
                "product_id": product_b.id,
                "combo_item_id": combos[1].combo_item_ids.id,
                "linked_line_id": combo_line.id,
            }),
        ]

        lines_to_report = self.sections_sale_order._get_order_lines_to_report()

        subsection_summary_lines = lines_to_report[0]._get_grouped_section_summary()
        self.assertEqual(len(subsection_summary_lines), 1)
        self.assertEqual(subsection_summary_lines[0]["price_subtotal"], 10.00)

    def test_sale_order_sections_totals(self):
        """Ensure section totals are computed correctly.

        A `line_section` should aggregate the subtotals of all following product
        order lines that belong to it, including those under nested subsections.
        Aggregation must stop when another section or subsection is encountered.
        """
        self.assertEqual(
            self.sections_sale_order.order_line[1]._get_section_totals("price_subtotal"),
            sum(self.sections_sale_order.order_line[1:].mapped("price_subtotal")),
        )
        self.assertEqual(
            self.sections_sale_order.order_line[3]._get_section_totals("price_subtotal"),
            sum(self.sections_sale_order.order_line[4:7].mapped("price_subtotal")),
        )
        self.assertEqual(
            self.sections_sale_order.order_line[7]._get_section_totals("price_subtotal"),
            sum(self.sections_sale_order.order_line[8:].mapped("price_subtotal")),
        )

    def test_section_qty_uom_defaults(self):
        """Sections and subsections default to a quantity of 1 Unit, other lines have none."""
        order = self.sections_sale_order
        order.order_line = [Command.create({"name": "Note", "display_type": "line_note"})]
        sections = order.order_line.filtered(
            lambda line: line.display_type in ("line_section", "line_subsection")
        )
        self.assertRecordValues(
            sections, [{"section_qty": 1.0, "section_uom_id": self.uom_unit.id}] * len(sections)
        )
        other_lines = order.order_line - sections
        self.assertRecordValues(
            other_lines, [{"section_qty": 0.0, "section_uom_id": False}] * len(other_lines)
        )

    def test_batch_onchange_sol(self):
        """`batch_onchange_sol` recomputes each line from its own changes, keyed by line id."""
        order = self.sections_sale_order
        saved_line = order.order_line[2]  # Sec1-r1
        fields_spec = {"product_uom_qty": {}, "price_subtotal": {}}

        result = self.env["sale.order"].batch_onchange_sol(
            {
                str(saved_line.id): {
                    "ids": saved_line.ids,
                    "changes": {"product_uom_qty": 3.0},
                    "changed_fields": ["product_uom_qty"],
                },
                "virtual_1": {
                    "ids": [],
                    "changes": {"product_id": self.product.id, "product_uom_qty": 4.0},
                    "changed_fields": ["product_uom_qty"],
                },
            },
            {"order_id": {"id": order.id}},
            fields_spec,
        )

        self.assertEqual(set(result), {str(saved_line.id), "virtual_1"})
        self.assertEqual(result[str(saved_line.id)]["price_subtotal"], 60.0)
        self.assertEqual(result["virtual_1"]["price_subtotal"], 80.0)
        self.assertEqual(saved_line.product_uom_qty, 1.0, "Onchange shouldn't write on the line")
