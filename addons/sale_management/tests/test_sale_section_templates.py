from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged("post_install", "-at_install")
class TestSaleSectionTemplates(SaleCommon):
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
                Command.create({"name": "Sec2", "display_type": "line_section"}),
                Command.create({
                    "name": "Sec2-r1",
                    "product_id": cls.product.id,
                    "tax_ids": cls.tax_2.ids,
                    "price_unit": 200,
                }),
                Command.create({
                    "name": "Sec2-r2",
                    "product_id": cls.product.id,
                    "tax_ids": (cls.tax_1 + cls.tax_2).ids,
                    "price_unit": 300,
                }),
                Command.create({
                    "name": "Sec2-r3 (Productless SOL)",
                    "price_unit": 420,
                    "discount": 15,
                    "tax_ids": (cls.tax_1 + cls.tax_2).ids,
                    "product_uom_id": cls.uom_unit.id,
                }),
            ],
        })

    def _get_section_templates(self, company=None):
        company_id = company.id or self.env.company.id
        templates = self.env["sale.order.template"].get_section_templates(company_id)
        return self.env["sale.order.template"].browse([t["id"] for t in templates])

    def test_sale_order_section_templates(self):
        order = self.sections_sale_order
        section_line = order.order_line[1]

        # First save
        section_line.save_section_template()

        templates = self._get_section_templates(order.company_id)
        self.assertEqual(len(templates), 1, "One new section template should be created")

        expected_lines = section_line._get_section_lines() + section_line
        self.assertEqual(
            len(templates[0].sale_order_template_line_ids),
            len(expected_lines),
            "Section template should have same number of lines as section",
        )

        # Modify and save again
        order.order_line[4].is_optional = True
        section_line.save_section_template()

        updated_templates = self._get_section_templates(order.company_id)
        self.assertEqual(
            len(updated_templates),
            1,
            "Template should not be duplicated for same section in same order",
        )

        self.assertTrue(
            updated_templates[0].sale_order_template_line_ids[3].is_optional,
            "Template should reflect updated lines",
        )

    def test_productless_sotl_in_section_template(self):
        order = self.sections_sale_order

        section_line = order.order_line.filtered(
            lambda line: line.display_type == "line_section" and line.name == "Sec2"
        )

        section_line.save_section_template()

        template = self._get_section_templates(order.company_id)

        productless_template_line = template.sale_order_template_line_ids.filtered(
            lambda line: line.name == "Sec2-r3 (Productless SOL)"
        )

        self.assertRecordValues(
            productless_template_line,
            [{"price_unit": 420, "discount": 15, "tax_ids": (self.tax_1 + self.tax_2).ids}],
        )

        self.assertEqual(
            template.currency_id, order.currency_id, "Currency should be taken from SO"
        )

    def test_section_template_keeps_section_qty_uom(self):
        """Section quantity and UoM should survive saving a section as template and reapplying it."""
        order = self.sections_sale_order
        section_line = order.order_line[1]  # Sec1
        subsection_line = order.order_line[3]  # Sec1-Sub1
        section_line.write({"section_qty": 3.0, "section_uom_id": self.uom_dozen.id})
        subsection_line.section_qty = 2.0

        section_line.save_section_template()
        template = self._get_section_templates(order.company_id)
        template_lines = template.sale_order_template_line_ids
        self.assertRecordValues(
            template_lines,
            [
                {"name": "Sec1", "section_qty": 3.0, "section_uom_id": self.uom_dozen.id},
                {"name": "Sec1-r1", "section_qty": 0.0, "section_uom_id": False},
                {"name": "Sec1-Sub1", "section_qty": 2.0, "section_uom_id": self.uom_unit.id},
                {"name": "Sec1-Sub1-r1", "section_qty": 0.0, "section_uom_id": False},
                {"name": "Sec1-Sub1-r2", "section_qty": 0.0, "section_uom_id": False},
                {"name": "Sec1-Sub1-r3", "section_qty": 0.0, "section_uom_id": False},
            ],
        )

        # Saving again should update the existing template
        section_line.section_qty = 4.0
        subsection_line.section_uom_id = self.uom_dozen
        section_line.save_section_template()
        template = self._get_section_templates(order.company_id)
        self.assertEqual(len(template), 1)
        self.assertRecordValues(
            template.sale_order_template_line_ids.filtered("display_type"),
            [
                {"name": "Sec1", "section_qty": 4.0, "section_uom_id": self.uom_dozen.id},
                {"name": "Sec1-Sub1", "section_qty": 2.0, "section_uom_id": self.uom_dozen.id},
            ],
        )

        # Applying the section template should give back the section quantities and UoMs
        lines_values = template.prepare_section_template_order_lines(
            {"order_id": {"id": order.id}},
            order.fiscal_position_id.id,
            order.company_id.id,
            order.currency_id.id,
            {
                field_name: {}
                for field_name in (
                    "name",
                    "display_type",
                    "sequence",
                    "is_optional",
                    "collapse_composition",
                    "collapse_prices",
                    "product_id",
                    "product_uom_qty",
                    "product_uom_id",
                    "product_no_variant_attribute_value_ids",
                    "product_custom_attribute_value_ids",
                    "price_unit",
                    "discount",
                    "tax_ids",
                    "section_qty",
                    "section_uom_id",
                )
            },
        )
        self.assertEqual(
            [
                (values["name"], values["section_qty"], values["section_uom_id"])
                for values in lines_values
                if values["name"] in ("Sec1", "Sec1-Sub1", "Sec1-r1")
            ],
            [
                ("Sec1", 4.0, self.uom_dozen.id),
                ("Sec1-r1", 0.0, False),
                ("Sec1-Sub1", 2.0, self.uom_dozen.id),
            ],
        )
