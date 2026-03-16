from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged("post_install", "-at_install")
class TestSaleSectionTemplates(SaleCommon):
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
            ],
        })

    def test_sale_order_section_templates(self):
        order = self.sections_sale_order
        section_line = order.order_line[1]

        def _get_templates():
            templates = self.env["sale.order.template"].get_section_templates(order.company_id.id)
            return self.env["sale.order.template"].browse([t["id"] for t in templates])

        # First save
        section_line.save_section_template()

        templates = _get_templates()
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

        updated_templates = _get_templates()
        self.assertEqual(
            len(updated_templates),
            1,
            "Template should not be duplicated for same section in same order",
        )

        self.assertTrue(
            updated_templates[0].sale_order_template_line_ids[3].is_optional,
            "Template should reflect updated lines",
        )
