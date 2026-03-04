from odoo import Command
from odoo.tests import tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestSaleOrderLine(SaleCommon):

    def test_get_description_following_lines(self):
        desc = "First line\nSecond line\nThird line"
        product_2 = self._create_product(name="Test product 2", description_sale=desc)
        sale_order = self._create_so(company_id=self.company.id, order_line=[
            Command.create({'product_id': self.product.id}),
            Command.create({'product_id': self.product.id}),
            Command.create({'product_id': product_2.id}),
            Command.create({'product_id': product_2.id}),
            Command.create({'product_id': product_2.id}),
            Command.create({'product_id': product_2.id}),
        ])

        added_desc = "Some important description that should be at the top"
        added_desc_2 = "Some even more important description"
        added_desc_3 = "The most important description"
        added_desc_before = "Some less important description that should be at the bottom"

        sale_order.order_line[1].name += "\n" + added_desc
        sale_order.order_line[3].name += "\n" + added_desc
        sale_order.order_line[4].name += "\n" + added_desc + "\n" + added_desc_2 + "\n" + added_desc_3
        first_newline = sale_order.order_line[5].name.find("\n", 1)
        sale_order.order_line[5].name = (
            sale_order.order_line[5].name[:first_newline] +
            "\n" + added_desc_before +
            sale_order.order_line[5].name[first_newline:]
            + "\n" + added_desc
        )

        split_desc = desc.splitlines()
        cases = [
            (0, []),
            (1, [added_desc]),
            (2, split_desc),
            (3, [added_desc, *split_desc]),
            (4, [added_desc_3, added_desc_2, added_desc, *split_desc]),
            (5, [added_desc, *split_desc, added_desc_before]),
        ]
        for line_index, expected in cases:
            line = sale_order.order_line[line_index]
            with self.subTest(product=line.name.splitlines()[0]):
                self.assertListEqual(list(line.get_description_following_lines()), expected)

    def test_get_other_lang_description_following_lines(self):
        self.env['res.lang']._activate_lang('fr_BE')
        desc_fr = "Première ligne\nDeuxième ligne\nTroisième ligne"
        self.product.with_context(lang="fr_BE").description_sale = desc_fr
        self.partner.lang = "fr_BE"

        sale_order_fr = self._create_so(partner_id=self.partner.id, company_id=self.company.id,
            order_line=[Command.create({'product_id': self.product.id})])

        added_desc = "Some important description that should be at the top"
        added_desc_2 = "Some even more important description"
        added_desc_3 = "The most important description"
        sale_order_fr.order_line[0].name += "\n" + added_desc + "\n" + added_desc_2 + "\n" + added_desc_3

        following_lines = list(sale_order_fr.order_line[0].get_description_following_lines())
        split_desc = desc_fr.splitlines()
        self.assertListEqual(following_lines, [added_desc_3, added_desc_2, added_desc, *split_desc])
