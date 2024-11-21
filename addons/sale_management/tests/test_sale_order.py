# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import chain

from odoo.fields import Command
from odoo.tests import Form, tagged

from odoo.addons.sale_management.tests.common import SaleManagementCommon


@tagged('-at_install', 'post_install')
class TestSaleOrder(SaleManagementCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # some variables to ease asserts in tests
        cls.pub_product_price = 100.0
        cls.pl_product_price = 80.0
        cls._enable_discounts()
        cls.tpl_discount = 10.0
        cls.pl_discount = (cls.pub_product_price - cls.pl_product_price) * 100 / cls.pub_product_price
        cls.merged_discount = 100.0 - (100.0 - cls.pl_discount) * (100.0 - cls.tpl_discount) / 100.0

        cls.pub_option_price = 200.0
        cls.pl_option_price = 100.0
        cls.tpl_option_discount = 20.0
        cls.pl_option_discount = (cls.pub_option_price - cls.pl_option_price) * 100 / cls.pub_option_price
        cls.merged_option_discount = 100.0 - (100.0 - cls.pl_option_discount) * (100.0 - cls.tpl_option_discount) / 100.0

        # create some products
        cls.product_1, cls.optional_product = cls.env['product.product'].create([
            {
                'name': 'Product 1',
                'lst_price': cls.pub_product_price,
                'description_sale': "This is a product description"
            }, {
                'name': 'Optional product',
                'lst_price': cls.pub_option_price,
            }
        ])

        # create some quotation templates
        cls.quotation_template_no_discount = cls.env['sale.order.template'].create({
            'name': 'A quotation template',
            'sale_order_template_line_ids': [
                Command.create({
                    'product_id': cls.product_1.id,
                }),
            ],
            'sale_order_template_option_ids': [
                Command.create({
                    'product_id': cls.optional_product.id,
                }),
            ],
        })

        # create two pricelist with different discount policies (same total price)
        pricelist_rule_values = [
            Command.create({
                'name': 'Product 1 premium price',
                'applied_on': '1_product',
                'product_tmpl_id': cls.product_1.product_tmpl_id.id,
                'compute_price': 'fixed',
                'fixed_price': cls.pl_product_price,
            }),
            Command.create({
                'name': 'Optional product premium price',
                'applied_on': '1_product',
                'product_tmpl_id': cls.optional_product.product_tmpl_id.id,
                'compute_price': 'fixed',
                'fixed_price': cls.pl_option_price,
            }),
        ]
        percentage_pricelist_rule_values = [
            Command.create({
                'name': 'Product 1 premium price',
                'applied_on': '1_product',
                'product_tmpl_id': cls.product_1.product_tmpl_id.id,
                'compute_price': 'percentage',
                'percent_price': cls.pl_discount,
            }),
            Command.create({
                'name': 'Optional product premium price',
                'applied_on': '1_product',
                'product_tmpl_id': cls.optional_product.product_tmpl_id.id,
                'compute_price': 'percentage',
                'percent_price': cls.pl_option_discount,
            }),
        ]

        (
            cls.discount_included_price_list,
            cls.discount_excluded_price_list
        ) = cls.env['product.pricelist'].create([
            {
                'name': 'Discount included Pricelist',
                'item_ids': pricelist_rule_values,
            }, {
                'name': 'Discount excluded Pricelist',
                'item_ids': percentage_pricelist_rule_values,
            }
        ])

        # variable kept to reduce code diff
        cls.sale_order = cls.empty_order

    def test_01_template_without_pricelist(self):
        """
        This test checks that without any rule in the pricelist, the public price
        of the product is used in the sale order after selecting a
        quotation template.
        """
        # first case, without discount in the quotation template
        self.sale_order.write({
            'sale_order_template_id': self.quotation_template_no_discount.id
        })
        self.sale_order._onchange_sale_order_template_id()

        self.assertEqual(
            len(self.sale_order.order_line),
            1,
            "The sale order shall contains the same number of products as"
            "the quotation template.")

        self.assertEqual(
            self.sale_order.order_line[0].product_id.id,
            self.product_1.id,
            "The sale order shall contains the same products as the"
            "quotation template.")

        self.assertEqual(
            self.sale_order.order_line[0].price_unit,
            self.pub_product_price,
            "Without any price list and discount, the public price of"
            "the product shall be used.")

        self.assertEqual(
            len(self.sale_order.sale_order_option_ids),
            1,
            "The sale order shall contains the same number of optional products as"
            "the quotation template.")

        self.assertEqual(
            self.sale_order.sale_order_option_ids[0].product_id.id,
            self.optional_product.id,
            "The sale order shall contains the same optional products as the"
            "quotation template.")

        self.assertEqual(
            self.sale_order.sale_order_option_ids[0].price_unit,
            self.pub_option_price,
            "Without any price list and discount, the public price of"
            "the optional product shall be used.")

        # add the option to the order
        self.sale_order.sale_order_option_ids[0].button_add_to_order()

        self.assertEqual(
            len(self.sale_order.order_line),
            2,
            "When an option is added, a new order line is created")

        self.assertEqual(
            self.sale_order.order_line[1].product_id.id,
            self.optional_product.id,
            "The sale order shall contains the same products as the"
            "quotation template.")

        self.assertEqual(
            self.sale_order.order_line[1].price_unit,
            self.pub_option_price,
            "Without any price list and discount, the public price of"
            "the optional product shall be used.")

    def test_02_template_with_discount_included_pricelist(self):
        """
        This test checks that with a 'discount included' price list,
        the price used in the sale order is computed according to the
        price list.
        """

        # first case, without discount in the quotation template
        self.sale_order.write({
            'pricelist_id': self.discount_included_price_list.id,
            'sale_order_template_id': self.quotation_template_no_discount.id
        })
        self.sale_order._onchange_sale_order_template_id()

        self.assertEqual(
            self.sale_order.order_line[0].price_unit,
            self.pl_product_price,
            "If a pricelist is set, the product price shall be computed"
            "according to it.")

        self.assertEqual(
            self.sale_order.sale_order_option_ids[0].price_unit,
            self.pl_option_price,
            "If a pricelist is set, the optional product price shall"
            "be computed according to it.")

        # add the option to the order
        self.sale_order.sale_order_option_ids[0].button_add_to_order()

        self.assertEqual(
            self.sale_order.order_line[1].price_unit,
            self.pl_option_price,
            "If a pricelist is set, the optional product price shall"
            "be computed according to it.")

    def test_03_template_with_discount_excluded_pricelist(self):
        """
        This test checks that with a 'discount excluded' price list,
        the price used in the sale order is the product public price and
        the discount is computed according to the price list.
        """
        self.sale_order.write({
            'pricelist_id': self.discount_excluded_price_list.id,
            'sale_order_template_id': self.quotation_template_no_discount.id
        })
        self.sale_order._onchange_sale_order_template_id()

        self.assertEqual(
            self.sale_order.order_line[0].price_unit,
            self.pub_product_price,
            "If a pricelist is set without discount included, the unit "
            "price shall be the public product price.")

        self.assertEqual(
            self.sale_order.order_line[0].price_subtotal,
            self.pl_product_price,
            "If a pricelist is set without discount included, the subtotal "
            "price shall be the price computed according to the price list.")

        self.assertEqual(
            self.sale_order.order_line[0].discount,
            self.pl_discount,
            "If a pricelist is set without discount included, the discount "
            "shall be computed according to the price unit and the subtotal."
            "price")

        self.assertEqual(
            self.sale_order.sale_order_option_ids[0].price_unit,
            self.pub_option_price,
            "If a pricelist is set without discount included, the unit "
            "price shall be the public optional product price.")

        self.assertEqual(
            self.sale_order.sale_order_option_ids[0].discount,
            self.pl_option_discount,
            "If a pricelist is set without discount included, the discount "
            "shall be computed according to the optional price unit and"
            "the subtotal price.")

        # add the option to the order
        self.sale_order.sale_order_option_ids[0].button_add_to_order()

        self.assertEqual(
            self.sale_order.order_line[1].price_unit,
            self.pub_option_price,
            "If a pricelist is set without discount included, the unit "
            "price shall be the public optional product price.")

        self.assertEqual(
            self.sale_order.order_line[1].price_subtotal,
            self.pl_option_price,
            "If a pricelist is set without discount included, the subtotal "
            "price shall be the price computed according to the price list.")

        self.assertEqual(
            self.sale_order.order_line[1].discount,
            self.pl_option_discount,
            "If a pricelist is set without discount included, the discount "
            "shall be computed according to the price unit and the subtotal."
            "price")

    def test_04_update_pricelist_option_line(self):
        """
        This test checks that option line's values are correctly
        updated after a pricelist update
        """
        self.sale_order.write({
            'sale_order_template_id': self.quotation_template_no_discount.id
        })
        self.sale_order._onchange_sale_order_template_id()

        self.assertEqual(
            self.sale_order.sale_order_option_ids[0].price_unit,
            self.pub_option_price,
            "If no pricelist is set, the unit price shall be the option's product price.")

        self.assertEqual(
            self.sale_order.sale_order_option_ids[0].discount, 0,
            "If no pricelist is set, the discount should be 0.")

        self.sale_order.write({
            'pricelist_id': self.discount_included_price_list.id,
        })
        self.sale_order._recompute_prices()

        self.assertEqual(
            self.sale_order.sale_order_option_ids[0].price_unit,
            self.pl_option_price,
            "If a pricelist is set with discount included,"
            " the unit price shall be the option's product discounted price.")

        self.assertEqual(
            self.sale_order.sale_order_option_ids[0].discount, 0,
            "If a pricelist is set with discount included,"
            " the discount should be 0.")

        self.sale_order.write({
            'pricelist_id': self.discount_excluded_price_list.id,
        })
        self.sale_order._recompute_prices()

        self.assertEqual(
            self.sale_order.sale_order_option_ids[0].price_unit,
            self.pub_option_price,
            "If a pricelist is set without discount included,"
            " the unit price shall be the option's product sale price.")

        self.assertEqual(
            self.sale_order.sale_order_option_ids[0].discount,
            self.pl_option_discount,
            "If a pricelist is set without discount included,"
            " the discount should be correctly computed.")

    def test_option_creation(self):
        """Make sure the product uom is automatically added to the option when the product is specified"""
        order_form = Form(self.sale_order)
        with order_form.sale_order_option_ids.new() as option:
            option.product_id = self.product_1
        order = order_form.save()
        self.assertTrue(bool(order.sale_order_option_ids.uom_id))

    def test_option_price_unit_is_not_recomputed(self):
        """
        Verifies that user defined price unit for optional products remains the same after
        update of quantities.
        """

        sale_order_with_option = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'sale_order_option_ids': [Command.create({
                'product_id': self.optional_product.id,
                'price_unit': 10,
            })],
        })
        sale_order_with_option.sale_order_option_ids.add_option_to_order()

        # after changing the quantity of the product, the price unit should not be recomputed
        sale_order_with_option.order_line.product_uom_qty = 10
        self.assertEqual(sale_order_with_option.sale_order_option_ids.price_unit, 10)

    def test_reload_template_translations(self):
        """
        Check that quotation template gets reloaded with correct translations on partner change.
        """
        # Add some display type lines to the template
        self.quotation_template_no_discount.sale_order_template_line_ids = [
            Command.create({
                'name': "Section 1",
                'display_type': 'line_section',
            }),
            Command.create({
                'name': "Note 1",
                'display_type': 'line_note',
            }),
        ]
        # Remove product description to ease comparing before/after translations
        self.product_1.description_sale = None

        # Commence activation of Dutch vernacular
        self.env['res.lang']._activate_lang('nl_NL')
        partner_NL = self.partner.copy({'lang': 'nl_NL', 'name': "Pieter-Jan Hollandman"})
        names_EN = ["Product 1", "Section 1", "Note 1", "Optional product"]
        names_NL = ["Artikel 1", "Sectie 1", "Nota 1", "Optioneel artikel"]
        trans_dict = dict(zip(names_EN, names_NL))
        for record in chain(
            self.quotation_template_no_discount.sale_order_template_line_ids,
            self.quotation_template_no_discount.sale_order_template_line_ids.product_id,
            self.quotation_template_no_discount.sale_order_template_option_ids,
            self.quotation_template_no_discount.sale_order_template_option_ids.product_id,
        ):
            if not record.name:
                continue
            record.with_context(lang='nl_NL').name = trans_dict[record.name]

        # Create sale order form (and a way to retrieve line names)
        def get_form_field_names(form):
            return [
                form.order_line.edit(0).name,
                form.order_line.edit(1).name,
                form.order_line.edit(2).name,
                form.sale_order_option_ids.edit(0).name,
            ]

        order_form = Form(self.sale_order.browse())
        order_form.sale_order_template_id = self.quotation_template_no_discount

        # Sanity check English names
        self.assertSequenceEqual(
            get_form_field_names(order_form),
            names_EN,
            "Lines should be displayed in English for an American partner",
        )

        # Go Dutch
        order_form.partner_id = partner_NL
        self.assertSequenceEqual(
            get_form_field_names(order_form),
            names_NL,
            "Lines should be displayed in Dutch for a Dutch partner",
        )

        # Edit a line & change back to American partner
        with order_form.order_line.edit(0) as order_line:
            order_line.product_uom_qty += 1
        order_form.partner_id = self.partner
        self.assertSequenceEqual(
            get_form_field_names(order_form),
            names_NL,
            "Lines shouldn't change when edited",
        )

        # Reload template manually
        order_form.sale_order_template_id = self.quotation_template_no_discount
        self.assertSequenceEqual(
            get_form_field_names(order_form),
            names_EN,
            "Lines should change after manual template reload",
        )

        # Add a line & return to Dutch
        with order_form.sale_order_option_ids.new() as optional_product:
            optional_product.product_id = self.product
        order_form.partner_id = partner_NL
        self.assertSequenceEqual(
            get_form_field_names(order_form),
            names_EN,
            "Lines shouldn't change after a new one was added",
        )

        # Reload template, save, and change partner again
        order_form.sale_order_template_id = self.quotation_template_no_discount
        order_form.save()
        order_form.partner_id = self.partner
        self.assertSequenceEqual(
            get_form_field_names(order_form),
            names_NL,
            "Lines shouldn't change once saved",
        )

    def test_product_description_no_template_description(self):
        """
        Test case for when the product has a description, but the quotation template line does not.
        The final sale order line should use the product's description.
        """
        quotation_template_no_description = self.empty_order_template
        quotation_template_no_description.sale_order_template_line_ids = [
            Command.create({
                'product_id': self.product_1.id,
                'name': False,
            }),
        ]
        sale_order = self.empty_order
        sale_order.sale_order_template_id = quotation_template_no_description
        sale_order._onchange_sale_order_template_id()
        self.assertEqual(
            sale_order.order_line[0].name,
            f"{self.product_1.name}\n{self.product_1.description_sale}",
            "Sale order line should use product's description when no quotation template \
            description is set."
        )

    def test_product_description_with_template_description(self):
        """
        Test case for when both the product and the quotation template line have descriptions.
        The final sale order line should use the template's description.
        """
        quotation_template_with_description = self.empty_order_template
        quotation_template_with_description.sale_order_template_line_ids = [
            Command.create({
                'product_id': self.product_1.id,
                'name': "This is a template description",
            }),
        ]
        sale_order = self.empty_order
        sale_order.sale_order_template_id = quotation_template_with_description
        sale_order._onchange_sale_order_template_id()
        self.assertEqual(
            sale_order.order_line[0].name,
            quotation_template_with_description.sale_order_template_line_ids[0].name,
            "The sale order line should use the quotation template's description when both \
            product and the quotation template descriptions are set."
        )
