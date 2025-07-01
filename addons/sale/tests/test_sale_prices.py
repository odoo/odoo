# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from datetime import timedelta

from odoo import fields
from odoo.fields import Command
from odoo.tests import Form, tagged
from odoo.tools import float_compare, mute_logger, float_round

from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestSalePrices(SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._enable_discounts()
        cls.discount = 10  # %

        # Needed when run without demo data
        #   s.t. taxes creation doesn't fail
        belgium = cls.env.ref('base.be')
        cls.env.company.account_fiscal_country_id = belgium
        for model in ('account.tax', 'account.tax.group'):
            cls.env.add_to_compute(
                cls.env[model]._fields['country_id'],
                cls.env[model].search([('company_id', '=', cls.env.company.id)]),
            )

    def _create_discount_pricelist_rule(self, **additional_values):
        return self.env['product.pricelist.item'].create({
            'pricelist_id': self.pricelist.id,
            'compute_price': 'percentage',
            'percent_price': self.discount,
            **additional_values,
        })

    def test_pricelist_minimal_qty(self):
        """ Verify the quantity and uom are correctly provided to the pricelist API"""
        pricelist_rule = self._create_discount_pricelist_rule(
            min_quantity=4.0,
        )
        product_price = self.product.lst_price
        product_dozen_price = product_price * 12

        self.empty_order.order_line = [
            Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 3.0,
            }),
            Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 4.0,
            }),
            Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 5.0,
            }),
            Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 1.0,
                'product_uom': self.uom_dozen.id,
            }),
            Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 0.4,
                'product_uom': self.uom_dozen.id,
            }),
            Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 0.3,
                'product_uom': self.uom_dozen.id,
            })
        ]

        discounted_lines = self.empty_order.order_line.filtered('pricelist_item_id')
        self.assertEqual(discounted_lines, self.empty_order.order_line[1:5])
        self.assertEqual(discounted_lines.pricelist_item_id, pricelist_rule)
        self.assertTrue(all(not line.discount for line in self.empty_order.order_line - discounted_lines))
        self.assertEqual(
            discounted_lines.mapped('price_unit'),
            [product_price, product_price, product_dozen_price, product_dozen_price])
        self.assertEqual(discounted_lines.mapped('discount'), [self.discount]*len(discounted_lines))

        discounted_lines[0].product_uom_qty = 3.0
        self.assertFalse(discounted_lines[0].discount)

    def test_pricelist_dates(self):
        """ Verify the order date is correctly provided to the pricelist API"""
        today = fields.Datetime.today()
        tomorrow = today + timedelta(days=1)

        pricelist_rule = self._create_discount_pricelist_rule(
            date_start=today - timedelta(hours=1),
            date_end=today + timedelta(hours=23),
        )

        with freeze_time(today):
            # Create an order today, add line today, rule active today works
            self.empty_order.date_order = today
            order_line = self.env['sale.order.line'].create({
                'order_id': self.empty_order.id,
                'product_id': self.product.id,
            })

            self.assertEqual(order_line.pricelist_item_id, pricelist_rule)
            self.assertEqual(
                order_line.price_unit,
                self.product.lst_price)
            self.assertEqual(order_line.discount, 10)

            # Create an order tomorrow, add line today, rule active today doesn't work
            self.empty_order.date_order = tomorrow
            order_line = self.env['sale.order.line'].create({
                'order_id': self.empty_order.id,
                'product_id': self.product.id,
            })

            self.assertFalse(order_line.pricelist_item_id)
            self.assertEqual(order_line.price_unit, self.product.lst_price)
            self.assertEqual(order_line.discount, 0.0)

        with freeze_time(tomorrow):
            # Create an order tomorrow, add line tomorrow, rule active today doesn't work
            self.empty_order.date_order = tomorrow
            order_line = self.env['sale.order.line'].create({
                'order_id': self.empty_order.id,
                'product_id': self.product.id,
            })

            self.assertFalse(order_line.pricelist_item_id)
            self.assertEqual(order_line.price_unit, self.product.lst_price)
            self.assertEqual(order_line.discount, 0.0)

            # Create an order today, add line tomorrow, rule active today works
            self.empty_order.date_order = today
            order_line = self.env['sale.order.line'].create({
                'order_id': self.empty_order.id,
                'product_id': self.product.id,
            })

            self.assertEqual(order_line.pricelist_item_id, pricelist_rule)
            self.assertEqual(
                order_line.price_unit,
                self.product.lst_price)
            self.assertEqual(order_line.discount, 10)

        self.assertEqual(
            self.empty_order.amount_untaxed,
            self.product.lst_price * 3.8)  # Discount of 10% on 2 of the 4 sol

    def test_pricelist_product_context(self):
        """ Verify that the product attributes extra prices are correctly considered """
        no_variant_attribute = self.env['product.attribute'].create({
            'name': 'No Variant Test Attribute',
            'create_variant': 'no_variant',
            'value_ids': [
                Command.create({'name': 'A'}),
                Command.create({'name': 'B'}),
                Command.create({'name': 'C'}),
            ],
        })
        product_template = self.env['product.template'].create({
            'name': 'Test Template with no_variant attributes',
            'categ_id': self.product_category.id,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': no_variant_attribute.id,
                    'value_ids': [Command.set(no_variant_attribute.value_ids.ids)],
                }),
            ],
            'list_price': 75.0,
            'taxes_id': False,
        })

        # Specify an extra_price on a variant
        ptavs = product_template.attribute_line_ids.product_template_value_ids
        ptavs[0].price_extra = 5.0
        ptavs[2].price_extra = 25.0

        self.empty_order.order_line = [
            Command.create({
                'product_id': product_template.product_variant_id.id,
                'product_no_variant_attribute_value_ids': [Command.link(ptav.id)]
            })
            for ptav in ptavs
        ]

        order_lines = self.empty_order.order_line
        self.assertEqual(order_lines[0].price_unit, 80.0)
        self.assertEqual(order_lines[1].price_unit, 75.0)
        self.assertEqual(order_lines[2].price_unit, 100.0)

    def test_no_pricelist_rules(self):
        """Check currencies and uom conversions when no pricelist rule is available"""
        # UoM Conversion
        # Selling dozens => price_unit = 12*price by unit
        self.empty_order.order_line = [
            Command.create({
                'product_id': self.product.id,
                'product_uom': self.uom_dozen.id,
                'product_uom_qty': 2.0,
            }),
        ]
        self.assertEqual(self.empty_order.order_line.price_unit, 240.0)

        other_currency = self._enable_currency('EUR')
        pricelist_in_other_curr = self.env['product.pricelist'].create({
            'name': 'Test Pricelist (EUR)',
            'currency_id': other_currency.id,
        })
        with freeze_time('2022-08-19'):
            self.env['res.currency.rate'].create({
                'name': fields.Date.today(),
                'rate': 2.0,
                'currency_id': other_currency.id,
                'company_id': self.env.company.id,
            })
            order_in_other_currency = self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'pricelist_id': pricelist_in_other_curr.id,
                'order_line': [
                    Command.create({
                        'product_id': self.product.id,
                        'product_uom': self.uom_dozen.id,
                        'product_uom_qty': 2.0,
                    }),
                ]
            })
            # 20.0 (product price) * 24.0 (2 dozens) * 2.0 (price rate USD -> EUR)
            self.assertEqual(order_in_other_currency.amount_total, 960.0)

    def test_negative_discounts(self):
        """aka surcharges"""
        self.discount = -10
        rule = self._create_discount_pricelist_rule()
        order_line = self.env['sale.order.line'].create({
            'order_id': self.empty_order.id,
            'product_id': self.product.id,
        })
        self.assertEqual(order_line.price_unit, 22.0)
        self.assertEqual(order_line.pricelist_item_id, rule)

        # Even when the discount is supposed to be shown
        #   Surcharges shouldn't be shown to the user
        order_line = self.env['sale.order.line'].create({
            'order_id': self.empty_order.id,
            'product_id': self.product.id,
        })
        self.assertEqual(order_line.price_unit, 22.0)
        self.assertEqual(order_line.pricelist_item_id, rule)

    def test_pricelist_based_on_another(self):
        """ Test price and discount are correctly applied with a pricelist based on an other one"""
        self.product.lst_price = 100

        base_pricelist = self.env['product.pricelist'].create({
            'name': 'First pricelist',
            'item_ids': [Command.create({
                'compute_price': 'percentage',
                'base': 'list_price',
                'percent_price': 10,
                'applied_on': '3_global',
                'name': 'First discount',
            })],
        })

        self.pricelist.write({
            'item_ids': [Command.create({
                'compute_price': 'percentage',
                'base': 'pricelist',
                'base_pricelist_id': base_pricelist.id,
                'percent_price': 10,
                'applied_on': '3_global',
                'name': 'Second discount',
            })],
        })

        self.empty_order.write({
            'date_order': '2018-07-11',
        })

        order_line = self.env['sale.order.line'].create({
            'order_id': self.empty_order.id,
            'product_id': self.product.id,
        })

        self.assertEqual(order_line.pricelist_item_id, self.pricelist.item_ids)
        self.assertEqual(order_line.price_subtotal, 81, "Second pricelist rule not applied")
        self.assertEqual(
            order_line.discount, 19,
            "Discount not computed correctly based on both pricelists")

    def test_pricelist_with_another_currency(self):
        """ Test prices are correctly applied with a pricelist with another currency"""
        self.product.lst_price = 100

        currency_eur = self._enable_currency('EUR')
        self.env['res.currency.rate'].create({
            'name': '2018-07-11',
            'rate': 2.0,
            'currency_id': currency_eur.id,
            'company_id': self.env.company.id,
        })
        with mute_logger('odoo.models.unlink'):
            self.env['res.currency.rate'].search(
                [('currency_id', '=', self.env.company.currency_id.id)]
            ).unlink()
        new_uom = self.env['uom.uom'].create({
            'name': '10 units',
            'factor_inv': 10,
            'uom_type': 'bigger',
            'rounding': 1.0,
            'category_id': self.uom_unit.category_id.id,
        })

        # This pricelist doesn't show the discount
        pricelist_eur = self.env['product.pricelist'].create({
            'name': 'First pricelist',
            'currency_id': currency_eur.id,
            'item_ids': [Command.create({
                'compute_price': 'percentage',
                'base': 'list_price',
                'percent_price': 10,
                'applied_on': '3_global',
                'name': 'First discount'
            })],
        })

        self.empty_order.write({
            'date_order': '2018-07-12',
            'pricelist_id': pricelist_eur.id,
        })

        order_line = self.env['sale.order.line'].create({
            'order_id': self.empty_order.id,
            'product_id': self.product.id,
        })

        # force compute uom and prices
        self.assertEqual(order_line.discount, 10, "First pricelist rule not applied")
        order_line.product_uom = new_uom
        self.assertEqual(order_line.price_total, 1800, "First pricelist rule not applied")

    def test_multi_currency_discount(self):
        """Verify the currency used for pricelist price & discount computation."""
        product_1 = self.product
        product_2 = self.service_product

        # Make sure the company is in USD
        main_company = self.env.ref('base.main_company')
        main_curr = main_company.currency_id
        current_curr = self.env.company.currency_id  # USD
        other_curr = self._enable_currency('EUR')
        # main_company.currency_id = other_curr # product.currency_id when no company_id set
        other_company = self.env['res.company'].create({
            'name': 'Test',
            'currency_id': other_curr.id
        })
        user_in_other_company = self.env['res.users'].create({
            'company_id': other_company.id,
            'company_ids': [Command.set([other_company.id])],
            'name': 'E.T',
            'login': 'hohoho',
        })
        with mute_logger('odoo.models.unlink'):
            self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': '2010-01-01',
            'rate': 2.0,
            'currency_id': main_curr.id,
            'company_id': False,
        })

        product_1.company_id = False
        product_2.company_id = False

        self.assertEqual(product_1.currency_id, main_curr)
        self.assertEqual(product_2.currency_id, main_curr)
        self.assertEqual(product_1.cost_currency_id, current_curr)
        self.assertEqual(product_2.cost_currency_id, current_curr)

        product_1_ctxt = product_1.with_user(user_in_other_company)
        product_2_ctxt = product_2.with_user(user_in_other_company)
        self.assertEqual(product_1_ctxt.currency_id, main_curr)
        self.assertEqual(product_2_ctxt.currency_id, main_curr)
        self.assertEqual(product_1_ctxt.cost_currency_id, other_curr)
        self.assertEqual(product_2_ctxt.cost_currency_id, other_curr)

        product_1.lst_price = 100.0
        product_2_ctxt.standard_price = 10.0 # cost is company_dependent

        pricelist = self.env['product.pricelist'].create({
            'name': 'Test multi-currency',
            'company_id': False,
            'currency_id': other_curr.id,
            'item_ids': [
                Command.create({
                    'base': 'list_price',
                    'product_id': product_1.id,
                    'compute_price': 'percentage',
                    'percent_price': 20,
                }),
                Command.create({
                    'base': 'standard_price',
                    'product_id': product_2.id,
                    'compute_price': 'percentage',
                    'percent_price': 10,
                })
            ]
        })

        # Create a SO in the other company
        ##################################
        # product_currency = main_company.currency_id when no company_id on the product

        # CASE 1:
        # company currency = so currency
        # product_1.currency != so currency
        # product_2.cost_currency_id = so currency
        sales_order = product_1_ctxt.with_context(mail_notrack=True, mail_create_nolog=True).env['sale.order'].create({
            'partner_id': user_in_other_company.partner_id.id,
            'pricelist_id': pricelist.id,
            'order_line': [
                Command.create({
                    'product_id': product_1.id,
                    'product_uom_qty': 1.0
                }),
                Command.create({
                    'product_id': product_2.id,
                    'product_uom_qty': 1.0
                })
            ]
        })

        so_line_1 = sales_order.order_line[0]
        so_line_2 = sales_order.order_line[1]
        self.assertEqual(so_line_1.discount, 20)
        self.assertEqual(so_line_1.price_unit, 50.0)
        self.assertEqual(so_line_2.discount, 10)
        self.assertEqual(so_line_2.price_unit, 10)

        # CASE 2
        # company currency != so currency
        # product_1.currency == so currency
        # product_2.cost_currency_id != so currency
        pricelist.currency_id = main_curr
        sales_order = product_1_ctxt.with_context(mail_notrack=True, mail_create_nolog=True).env['sale.order'].create({
            'partner_id': user_in_other_company.partner_id.id,
            'pricelist_id': pricelist.id,
            'order_line': [
                # Verify discount is considered in create hack
                Command.create({
                    'product_id': product_1.id,
                    'product_uom_qty': 1.0
                }),
                Command.create({
                    'product_id': product_2.id,
                    'product_uom_qty': 1.0
                })
            ]
        })

        so_line_1 = sales_order.order_line[0]
        so_line_2 = sales_order.order_line[1]
        self.assertEqual(so_line_1.discount, 20)
        self.assertEqual(so_line_1.price_unit, 100.0)
        self.assertEqual(so_line_2.discount, 10)
        self.assertEqual(so_line_2.price_unit, 20)

    def test_update_prices(self):
        """Test prices recomputation on SO's.

        `_recompute_prices` is shown as a button to update
        prices when the pricelist was changed.
        """
        sale_order = self.sale_order
        so_amount = sale_order.amount_total
        start_so_amount = so_amount
        sale_order._recompute_prices()
        self.assertEqual(
            sale_order.amount_total, so_amount,
            "Updating the prices of an unmodified SO shouldn't modify the amounts")

        pricelist = sale_order.pricelist_id
        pricelist.item_ids = [
            Command.create({
                'percent_price': 5.0,
                'compute_price': 'percentage'
            })
        ]
        sale_order._recompute_prices()

        self.assertTrue(all(line.discount == 5 for line in sale_order.order_line))
        self.assertEqual(sale_order.amount_undiscounted, so_amount)
        self.assertEqual(sale_order.amount_total, 0.95*so_amount)

        pricelist.item_ids = [
            Command.create({
                'price_discount': 5,
                'compute_price': 'formula',
            })
        ]
        sale_order._recompute_prices()

        self.assertTrue(all(line.discount == 0 for line in sale_order.order_line))
        self.assertEqual(sale_order.amount_undiscounted, so_amount)
        self.assertEqual(sale_order.amount_total, 0.95*so_amount)

        # Test taking off the pricelist
        sale_order.pricelist_id = False
        sale_order._recompute_prices()

        self.assertTrue(all(line.discount == 0 for line in sale_order.order_line))
        self.assertEqual(sale_order.amount_undiscounted, so_amount)
        self.assertEqual(
            sale_order.amount_total, start_so_amount,
            "The SO amount without pricelist should be the same than with an empty pricelist"
        )

    def test_manual_price_prevents_recompute(self):
        sale_order_line = self.sale_order.order_line[0]
        # Ensure initial price is set correctly
        self.assertEqual(sale_order_line.price_unit, 20.0)

        # Update the price manually and then change the quantity
        with Form(sale_order_line) as line:
            line.price_unit = 100.0
            line.product_uom_qty = 10

        self.assertEqual(
            sale_order_line.price_unit, 100.0,
            "Price should remain 100.0 after changing the quantity"
        )

        zero_price_product = self._create_product(list_price=0.0)
        self.assertEqual(zero_price_product.list_price, 0.0)
        so_line = self.env['sale.order.line'].create({
            'product_id': zero_price_product.id,
            'order_id': self.sale_order.id,
        })
        self.assertEqual(so_line.price_unit, 0.0)
        self.assertEqual(so_line.technical_price_unit, 0.0)

        with Form(so_line) as so_line:
            so_line.price_unit = 10.0
            so_line.product_uom_qty = 2.0
            so_line.save()

        self.assertEqual(so_line.price_unit, 10.0)

    # Taxes tests:
    # We do not rely on accounting common on purpose to avoid
    # all the useless setup not needed here.
    # If you need the accounting common (journals, ...), use/make another test class

    def test_sale_tax_mapping(self):
        tax_a, tax_b = self.env['account.tax'].create([{
            'name': 'Test tax A',
            'type_tax_use': 'sale',
            'price_include_override': 'tax_included',
            'amount': 15.0,
        }, {
            'name': 'Test tax B',
            'type_tax_use': 'sale',
            'amount': 6.0,
        }])

        country_belgium = self.env['res.country'].search([
            ('name', '=', 'Belgium'),
        ], limit=1)
        fiscal_pos = self.env['account.fiscal.position'].create({
            'name': 'Test Fiscal Position',
            'auto_apply': True,
            'country_id': country_belgium.id,
            'tax_ids': [Command.create({
                'tax_src_id': tax_a.id,
                'tax_dest_id': tax_b.id
            })]
        })

        # setting up partner:
        self.partner.country_id = country_belgium

        self.product.write({
            'lst_price': 115,
            'taxes_id': [Command.set(tax_a.ids)]
        })

        self.pricelist.write({
            'item_ids': [Command.create({
                'applied_on': '3_global',
                'compute_price': 'percentage',
                'percent_price': 54,
            })]
        })

        # creating SO
        self.empty_order.write({
            'fiscal_position_id': fiscal_pos.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
            })],
        })

        # Update Prices
        self.empty_order._recompute_prices()

        # Check that the discount displayed is the correct one
        self.assertEqual(
            self.empty_order.order_line.discount, 54,
            "Wrong discount computed for specified product & pricelist"
        )
        # Additional to check for overall consistency
        self.assertEqual(
            self.empty_order.order_line.price_unit, 100,
            "Wrong unit price computed for specified product & pricelist"
        )
        self.assertEqual(
            self.empty_order.order_line.price_subtotal, 46,
            "Wrong subtotal price computed for specified product & pricelist"
        )
        self.assertEqual(
            self.empty_order.order_line.tax_id.id, tax_b.id,
            "Wrong tax applied for specified product & pricelist"
        )

    def test_fiscalposition_application(self):
        """Test application of a fiscal position mapping
        price included to price included tax
        """
        # If test is run without demo data
        # pricelists are not automatically enabled
        self._enable_pricelists()
        pricelist = self.pricelist
        partner = self.partner

        (
            tax_fixed_incl,
            tax_fixed_excl,
            tax_include_src,
            tax_include_dst,
            tax_exclude_src,
            tax_exclude_dst,
        ) = self.env['account.tax'].create([{
            'name': "fixed include",
            'amount': 10.00,
            'amount_type': 'fixed',
            'price_include_override': 'tax_included',
        }, {
            'name': "fixed exclude",
            'amount': 10.00,
            'amount_type': 'fixed',
            'price_include_override': 'tax_excluded',
        }, {
            'name': "Include 21%",
            'amount': 21.00,
            'amount_type': 'percent',
            'price_include_override': 'tax_included',
        }, {
            'name': "Include 6%",
            'amount': 6.00,
            'amount_type': 'percent',
            'price_include_override': 'tax_included',
        }, {
            'name': "Exclude 15%",
            'amount': 15.00,
            'amount_type': 'percent',
            'price_include_override': 'tax_excluded',
        }, {
            'name': "Exclude 21%",
            'amount': 21.00,
            'amount_type': 'percent',
            'price_include_override': 'tax_excluded',
        }])

        (
            product_tmpl_a,
            product_tmpl_b,
            product_tmpl_c,
            product_tmpl_d,
        ) = self.env['product.template'].create([{
            'name': "Voiture",
            'list_price': 121,
            'taxes_id': [Command.set([tax_include_src.id])]
        }, {
            'name': "Voiture",
            'list_price': 100,
            'taxes_id': [Command.set([tax_exclude_src.id])]
        }, {
            'name': "Voiture",
            'list_price': 100,
            'taxes_id': [Command.set([tax_fixed_incl.id, tax_exclude_src.id])]
        }, {
            'name': "Voiture",
            'list_price': 100,
            'taxes_id': [Command.set([tax_fixed_excl.id, tax_include_src.id])]
        }])

        (
            fpos_incl_incl,
            fpos_excl_incl,
            fpos_incl_excl,
            fpos_excl_excl,
        ) = self.env['account.fiscal.position'].create([{
            'name': "incl -> incl",
            'sequence': 1,
            'tax_ids': [Command.create({
                'tax_src_id': tax_include_src.id,
                'tax_dest_id': tax_include_dst.id,
            })]
        }, {
            'name': "excl -> incl",
            'sequence': 2,
            'tax_ids': [Command.create({
                'tax_src_id': tax_exclude_src.id,
                'tax_dest_id': tax_include_dst.id,
            })]
        }, {
            'name': "incl -> excl",
            'sequence': 3,
            'tax_ids': [Command.create({
                'tax_src_id': tax_include_src.id,
                'tax_dest_id': tax_exclude_dst.id,
            })]
        }, {
            'name': "excl -> excp",
            'sequence': 4,
            'tax_ids': [Command.create({
                'tax_src_id': tax_exclude_src.id,
                'tax_dest_id': tax_exclude_dst.id,
            })]
        }])

        # Create the SO with one SO line and apply a pricelist and fiscal position on it
        # Then check if price unit and price subtotal matches the expected values

        SaleOrder = self.env['sale.order']

        # Test Mapping included to included
        order_form = Form(SaleOrder)
        order_form.partner_id = partner
        order_form.pricelist_id = pricelist
        order_form.fiscal_position_id = fpos_incl_incl
        with order_form.order_line.new() as line:
            line.name = product_tmpl_a.product_variant_id.name
            line.product_id = product_tmpl_a.product_variant_id
            line.product_uom_qty = 1.0
        sale_order = order_form.save()
        self.assertRecordValues(sale_order.order_line, [{'price_unit': 106, 'price_subtotal': 100}])

        # Test Mapping excluded to included
        order_form = Form(SaleOrder)
        order_form.partner_id = partner
        order_form.pricelist_id = pricelist
        order_form.fiscal_position_id = fpos_excl_incl
        with order_form.order_line.new() as line:
            line.name = product_tmpl_b.product_variant_id.name
            line.product_id = product_tmpl_b.product_variant_id
            line.product_uom_qty = 1.0
        sale_order = order_form.save()
        self.assertRecordValues(sale_order.order_line, [{'price_unit': 100, 'price_subtotal': 94.34}])

        # Test Mapping included to excluded
        order_form = Form(SaleOrder)
        order_form.partner_id = partner
        order_form.pricelist_id = pricelist
        order_form.fiscal_position_id = fpos_incl_excl
        with order_form.order_line.new() as line:
            line.name = product_tmpl_a.product_variant_id.name
            line.product_id = product_tmpl_a.product_variant_id
            line.product_uom_qty = 1.0
        sale_order = order_form.save()
        self.assertRecordValues(sale_order.order_line, [{'price_unit': 100, 'price_subtotal': 100}])

        # Test Mapping excluded to excluded
        order_form = Form(SaleOrder)
        order_form.partner_id = partner
        order_form.pricelist_id = pricelist
        order_form.fiscal_position_id = fpos_excl_excl
        with order_form.order_line.new() as line:
            line.name = product_tmpl_b.product_variant_id.name
            line.product_id = product_tmpl_b.product_variant_id
            line.product_uom_qty = 1.0
        sale_order = order_form.save()
        self.assertRecordValues(sale_order.order_line, [{'price_unit': 100, 'price_subtotal': 100}])

        # Test Mapping (included,excluded) to (included, included)
        order_form = Form(SaleOrder)
        order_form.partner_id = partner
        order_form.pricelist_id = pricelist
        order_form.fiscal_position_id = fpos_excl_incl
        with order_form.order_line.new() as line:
            line.name = product_tmpl_c.product_variant_id.name
            line.product_id = product_tmpl_c.product_variant_id
            line.product_uom_qty = 1.0
        sale_order = order_form.save()
        self.assertRecordValues(sale_order.order_line, [{'price_unit': 100, 'price_subtotal': 84.91}])

        # Test Mapping (excluded,included) to (excluded, excluded)
        order_form = Form(SaleOrder)
        order_form.partner_id = partner
        order_form.pricelist_id = pricelist
        order_form.fiscal_position_id = fpos_incl_excl
        with order_form.order_line.new() as line:
            line.name = product_tmpl_d.product_variant_id.name
            line.product_id = product_tmpl_d.product_variant_id
            line.product_uom_qty = 1.0
        sale_order = order_form.save()
        self.assertRecordValues(sale_order.order_line, [{'price_unit': 100, 'price_subtotal': 100}])

    def test_so_tax_mapping(self):
        order = self.empty_order

        tax_include, tax_exclude = self.env['account.tax'].create([{
            'name': 'Include Tax',
            'amount': '21.00',
            'price_include_override': 'tax_included',
            'type_tax_use': 'sale',
        }, {
            'name': 'Exclude Tax',
            'amount': '0.00',
            'type_tax_use': 'sale',
        }])

        self.product.write({
            'list_price': 121,
            'taxes_id': [Command.set(tax_include.ids)]
        })

        fpos = self.env['account.fiscal.position'].create({
            'name': 'Test Fiscal Position',
            'sequence': 1,
            'tax_ids': [Command.create({
                'tax_src_id': tax_include.id,
                'tax_dest_id': tax_exclude.id,
            })],
        })

        order.write({
            'fiscal_position_id': fpos.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
            })]
        })

        # Check the unit price of SO line
        self.assertEqual(
            100, order.order_line[0].price_unit,
            "The included tax must be subtracted to the price")

    def test_so_tax_mapping_multicompany(self):
        tax_group = self.env['account.tax.group'].create({'name': "10%"})
        tax_include, tax_exclude = self.env['account.tax'].create([{
            'name': "10% Tax Inc.",
            'type_tax_use': 'sale',
            'amount': 10.0,
            'price_include_override': 'tax_included',
            'tax_group_id': tax_group.id,
        }, {
            'name': "10% Tax Exc.",
            'type_tax_use': 'sale',
            'amount': 0.0,
            'price_include_override': 'tax_excluded',
            'tax_group_id': tax_group.id,
        }])
        fpos = self.env['account.fiscal.position'].create({
            'name': "B2B",
            'tax_ids': [Command.create({
                'tax_src_id': tax_include.id,
                'tax_dest_id': tax_exclude.id,
            })],
        })
        self.product.write({
            'list_price': 110.0,
            'taxes_id': tax_include.ids,
        })
        branch_company = self.env['res.company'].create({
            'name': "Branch Co.",
            'parent_id': self.env.company.id,
            'account_fiscal_country_id': self.env.company.account_fiscal_country_id.id,
        })
        order = self.empty_order.with_company(branch_company)
        order.sudo().write({
            'company_id': branch_company.id,
            'fiscal_position_id': fpos.id,
            'user_id': False,
            'team_id': False,
            'order_line': [Command.create({'product_id': self.product.id})],
        })
        self.assertEqual(order.order_line.tax_id, tax_exclude, "Line tax should be mapped")
        self.assertAlmostEqual(
            order.order_line.price_unit, 100.0,
            msg="Tax should not be included in unit price",
        )

    def test_free_product_and_price_include_fixed_tax(self):
        """ Check that fixed tax include are correctly computed while the price_unit is 0 """
        taxes = self.env['account.tax'].create([{
            'name': 'BEBAT 0.05',
            'type_tax_use': 'sale',
            'amount_type': 'fixed',
            'amount': 0.05,
            'price_include_override': 'tax_included',
            'include_base_amount': True,
        }, {
            'name': 'Recupel 0.25',
            'type_tax_use': 'sale',
            'amount_type': 'fixed',
            'amount': 0.25,
            'price_include_override': 'tax_included',
            'include_base_amount': True,
        }])
        order = self.empty_order
        order.order_line = [Command.create({
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'price_unit': 0.0,
            'tax_id': [
                Command.set(taxes.ids),
            ],
        })]

        self.assertRecordValues(order.order_line, [{
            'price_tax': 0.3,
            'price_subtotal': -0.3,
            'price_total': 0.0,
        }])
        self.assertRecordValues(order, [{
            'amount_untaxed': -0.30,
            'amount_tax': 0.30,
            'amount_total': 0.0,
        }])

    def test_sale_with_taxes(self):
        """ Test SO with taxes applied on its lines and check subtotal applied on its lines and total applied on the SO """
        tax_include, tax_exclude = self.env['account.tax'].create([{
            'name': 'Tax with price include',
            'amount': 10,
            'price_include_override': 'tax_included',
        }, {
            'name': 'Tax with no price include',
            'amount': 10,
        }])

        # Apply taxes on the sale order lines
        self.sale_order.order_line[0].write({'tax_id': [Command.link(tax_include.id)]})
        self.sale_order.order_line[1].write({'tax_id': [Command.link(tax_exclude.id)]})

        for line in self.sale_order.order_line:
            if line.tax_id.price_include:
                price = line.price_unit * line.product_uom_qty - line.price_tax
            else:
                price = line.price_unit * line.product_uom_qty

            self.assertEqual(float_compare(line.price_subtotal, price, precision_digits=2), 0)

        self.assertAlmostEqual(
            self.sale_order.amount_total,
            self.sale_order.amount_untaxed + self.sale_order.amount_tax,
            places=2)

    def test_discount_and_untaxed_subtotal(self):
        """When adding a discount on a SO line, this test ensures that the untaxed amount to invoice is
        equal to the untaxed subtotal"""
        self.product.invoice_policy = 'delivery'
        order = self.empty_order

        order.order_line = [Command.create({
            'product_id': self.product.id,
            'product_uom_qty': 38,
            'price_unit': 541.26,
            'discount': 2.00,
        })]
        order.action_confirm()
        line = order.order_line
        self.assertEqual(line.untaxed_amount_to_invoice, 0)

        line.qty_delivered = 38
        # (541.26 - 0.02 * 541.26) * 38 = 20156.5224 ~= 20156.52
        self.assertEqual(line.price_subtotal, 20156.52)
        self.assertEqual(line.untaxed_amount_to_invoice, line.price_subtotal)

        # Same with an included-in-price tax
        order = order.copy()
        line = order.order_line
        line.tax_id = [Command.create({
            'name': 'Super Tax',
            'amount_type': 'percent',
            'amount': 15.0,
            'price_include_override': 'tax_included',
        })]
        order.action_confirm()
        self.assertEqual(line.untaxed_amount_to_invoice, 0)

        line.qty_delivered = 38
        # (541,26 / 1,15) * ,98 * 38 = 17527,410782609 ~= 17527.41
        self.assertEqual(line.price_subtotal, 17527.41)
        self.assertEqual(line.untaxed_amount_to_invoice, line.price_subtotal)

    def test_discount_and_amount_undiscounted(self):
        """When adding a discount on a SO line, this test ensures that amount undiscounted is
        consistent with the used tax"""
        order = self.empty_order

        order.order_line = [Command.create({
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'price_unit': 100.0,
            'discount': 1.00,
        })]
        order.action_confirm()
        order_line = order.order_line

        # test discount and qty 1
        self.assertEqual(order.amount_undiscounted, 100.0)
        self.assertEqual(order_line.price_subtotal, 99.0)

        # more quantity 1 -> 3
        order_line.write({
            'product_uom_qty': 3.0,
            'price_unit': 100.0,
            'discount': 1.0,
        })
        order.invalidate_recordset(['amount_undiscounted'])

        self.assertEqual(order.amount_undiscounted, 300.0)
        self.assertEqual(order_line.price_subtotal, 297.0)

        # undiscounted
        order_line.discount = 0.0
        self.assertEqual(order_line.price_subtotal, 300.0)
        self.assertEqual(order.amount_undiscounted, 300.0)

        # Same with an included-in-price tax
        order = order.copy()
        line = order.order_line
        line.tax_id = [Command.create({
            'name': 'Super Tax',
            'amount_type': 'percent',
            'amount': 10.0,
            'price_include_override': 'tax_included',
        })]
        line.discount = 50.0
        order.action_confirm()

        # 300 with 10% incl tax -> 272.72 total tax excluded without discount
        # 136.36 price tax excluded with discount applied
        self.assertEqual(order.amount_undiscounted, 272.72)
        self.assertEqual(line.price_subtotal, 136.36)

    def test_product_quantity_rounding(self):
        """When adding a sale order line, product quantity should be rounded
        according to decimal precision"""
        order = self.empty_order

        product_uom_qty = 0.333333
        order.order_line = [Command.create({
            'product_id': self.product.id,
            'product_uom_qty': product_uom_qty,
            'price_unit': 75.0,
        })]
        order.action_confirm()
        line = order.order_line
        quantity_precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        self.assertEqual(
            line.product_uom_qty, float_round(product_uom_qty, precision_digits=quantity_precision))
        expected_price_subtotal = line.currency_id.round(
            line.price_unit * float_round(product_uom_qty, precision_digits=quantity_precision))
        self.assertAlmostEqual(line.price_subtotal, expected_price_subtotal)
        self.assertEqual(order.amount_total, order.tax_totals.get('total_amount_currency'))

    def test_show_discount(self):
        """
            Test that discount is shown only when compute_price is percentage
            If compute_price is formula, discount should be included in price.
        """
        test_product_discount = self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100.0,
            'taxes_id': None,
        })
        test_product_incl_discount = self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100.0,
            'taxes_id': None,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': test_product_discount.id,
                    'product_uom_qty': 1.0,
                }),
                Command.create({
                    'product_id': test_product_incl_discount.id,
                    'product_uom_qty': 1,
                })
            ]
        })

        self.assertEqual(200, sale_order.amount_total)
        base_discount_pricelist = self.env['product.pricelist'].create({
            'name': 'Base Discount Pricelist',
            'item_ids': [
                Command.create({
                    'name': 'Discount',
                    'applied_on': '1_product',
                    'product_tmpl_id':  test_product_discount.product_tmpl_id.id,
                    'compute_price': 'percentage',
                    'percent_price': 10,
                }),
                Command.create({
                    'name': 'Formula',
                    'applied_on': '1_product',
                    'product_tmpl_id':  test_product_incl_discount.product_tmpl_id.id,
                    'compute_price': 'formula',
                    'price_discount': 10,
                }),
            ]})

        sale_order.pricelist_id = base_discount_pricelist
        sale_order._recompute_prices()
        show_discount_line = sale_order.order_line[0]
        included_discount_line = sale_order.order_line[1]

        self.assertEqual(show_discount_line.price_unit, 100)
        self.assertEqual(show_discount_line.price_subtotal, show_discount_line.price_unit * 0.9)
        self.assertEqual(show_discount_line.discount, 10)
        self.assertEqual(included_discount_line.price_unit, included_discount_line.price_subtotal)
        self.assertEqual(included_discount_line.discount, 0)

        # Test with discount based on other pricelist
        discount_pricelist = self.env['product.pricelist'].create({
            'name': 'Discount Pricelist',
            'item_ids': [
                Command.create({
                    'name': 'Discount based on pricelist',
                    'applied_on': '1_product',
                    'product_tmpl_id': test_product_discount.product_tmpl_id.id,
                    'compute_price': 'percentage',
                    'percent_price': 10,
                    'base': 'pricelist',
                    'base_pricelist_id': base_discount_pricelist.id,
                }),
            ]})
        sale_order.pricelist_id = discount_pricelist
        sale_order._recompute_prices()

        self.assertEqual(show_discount_line.price_unit, 100)
        self.assertEqual(show_discount_line.price_subtotal, show_discount_line.price_unit * 0.81)
        self.assertEqual(show_discount_line.discount, 19)
