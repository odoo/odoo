# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo import Command
from odoo.tests import Form, tagged
from odoo.tools import float_compare

from odoo.addons.delivery.tests.common import DeliveryCommon
from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestDeliveryCost(DeliveryCommon, SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._enable_uom()

        # the tests hereunder assume all the prices in USD
        cls.env.company.country_id = cls.env.ref('base.us').id

        cls.product.weight = 1.0
        cls.product_delivery_normal = cls._prepare_carrier_product(
            name='Normal Delivery Charges',
            list_price=10.0,
        )
        cls.normal_delivery = cls._prepare_carrier(
            product=cls.product_delivery_normal,
            name='Normal Delivery Charges',
            delivery_type='fixed',
            fixed_price=10.0,
        )
        cls.partner_4 = cls.env['res.partner'].create({
            'name': 'Another Customer',
            'child_ids': [
                Command.create({
                    'name': "Another Customer's Address",
                })
            ]
        })
        cls.partner_address_13 = cls.partner_4.child_ids
        cls.product_uom_hour = cls.env.ref('uom.product_uom_hour')

    def test_00_delivery_cost(self):
        # In order to test Carrier Cost
        # Create sales order with Normal Delivery Charges

        self.sale_normal_delivery_charges = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 750.00,
                })
            ],
        })
        # I add delivery cost in Sales order

        self.a_sale = self.env['account.account'].create({
            'code': 'X2020',
            'name': 'Product Sales - (test)',
            'account_type': 'income',
            'tag_ids': [Command.set(self.env.ref('account.account_tag_operating').ids)]
        })

        self.product_consultant = self.env['product.product'].create({
            'sale_ok': True,
            'list_price': 75.0,
            'standard_price': 30.0,
            'uom_id': self.product_uom_hour.id,
            'uom_po_id': self.product_uom_hour.id,
            'name': 'Service',
            'type': 'service'
        })

        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': self.sale_normal_delivery_charges.id,
            'default_carrier_id': self.normal_delivery.id
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()

        # I check sales order after added delivery cost

        line = self.sale_normal_delivery_charges.order_line.filtered_domain([
            ('product_id', '=', self.normal_delivery.product_id.id)])
        self.assertEqual(len(line), 1, "Delivery cost is not Added")

        zin = str(delivery_wizard.display_price) + " " + str(delivery_wizard.delivery_price) + ' ' + line.company_id.country_id.code + line.company_id.name
        self.assertEqual(float_compare(line.price_subtotal, 10.0, precision_digits=2), 0,
            "Delivery cost does not correspond to 10.0. %s %s" % (line.price_subtotal, zin))

        # I confirm the sales order

        self.sale_normal_delivery_charges.action_confirm()

        # Create one more sales order with Free Delivery Charges
        self.delivery_sale_order_cost = self.env['sale.order'].create({
            'partner_id': self.partner_4.id,
            'partner_invoice_id': self.partner_address_13.id,
            'partner_shipping_id': self.partner_address_13.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_consultant.id,
                    'product_uom_qty': 24,
                    'product_uom': self.product_uom_hour.id,
                    'price_unit': 75.00,
                }),
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 30,
                    'price_unit': 38.25,
                })
            ],
        })

        # I add free delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': self.delivery_sale_order_cost.id,
            'default_carrier_id': self.free_delivery.id
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()

        # I check sales order after adding delivery cost
        line = self.delivery_sale_order_cost.order_line.filtered_domain([
            ('product_id', '=', self.free_delivery.product_id.id)])

        self.assertEqual(len(line), 1, "Delivery cost is not Added")
        self.assertEqual(float_compare(line.price_subtotal, 0, precision_digits=2), 0,
            "Delivery cost is not correspond.")

        # I set default delivery policy
        self.env['res.config.settings'].create({}).execute()

    def test_01_delivery_cost_from_pricelist(self):
        """ This test aims to validate the use of a pricelist to compute the delivery cost in the case the associated
            product of the shipping method is defined in the pricelist """

        # Create pricelist with a custom price for the standard shipping method
        my_pricelist = self.env['product.pricelist'].create({
            'name': 'shipping_cost_change',
            'item_ids': [Command.create({
                'compute_price': 'fixed',
                'fixed_price': 5,
                'applied_on': '0_product_variant',
                'product_id': self.normal_delivery.product_id.id,
            })],
        })

        # Create sales order with Normal Delivery Charges
        sale_pricelist_based_delivery_charges = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'pricelist_id': my_pricelist.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 750.00,
            })],
        })

        # Add of delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_pricelist_based_delivery_charges.id,
            'default_carrier_id': self.normal_delivery.id
        }))
        self.assertEqual(delivery_wizard.delivery_price, 5.0, "Delivery cost does not correspond to 5.0 in wizard")
        delivery_wizard.save().button_confirm()

        line = sale_pricelist_based_delivery_charges.order_line.filtered_domain([
            ('product_id', '=', self.normal_delivery.product_id.id)])
        self.assertEqual(len(line), 1, "Delivery cost hasn't been added to SO")
        self.assertEqual(line.price_subtotal, 5.0, "Delivery cost does not correspond to 5.0")

    def test_02_delivery_cost_from_different_currency(self):
        """ This test aims to validate the use of a pricelist using a different currency to compute the delivery cost in
            the case the associated product of the shipping method is defined in the pricelist """

        # Create pricelist with a custom price for the standard shipping method
        my_pricelist = self.env['product.pricelist'].create({
            'name': 'shipping_cost_change',
            'item_ids': [Command.create({
                'compute_price': 'fixed',
                'fixed_price': 5,
                'applied_on': '0_product_variant',
                'product_id': self.normal_delivery.product_id.id,
            })],
            'currency_id': self.env.ref('base.EUR').id,
        })

        # Create sales order with Normal Delivery Charges
        sale_pricelist_based_delivery_charges = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'pricelist_id': my_pricelist.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 750.00,
            })],
        })

        # Add of delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_pricelist_based_delivery_charges.id,
            'default_carrier_id': self.normal_delivery.id
        }))
        self.assertEqual(delivery_wizard.delivery_price, 5.0, "Delivery cost does not correspond to 5.0 in wizard")
        delivery_wizard.save().button_confirm()

        line = sale_pricelist_based_delivery_charges.order_line.filtered_domain([
            ('product_id', '=', self.normal_delivery.product_id.id)])
        self.assertEqual(len(line), 1, "Delivery cost hasn't been added to SO")
        self.assertEqual(line.price_subtotal, 5.0, "Delivery cost does not correspond to 5.0")

    def test_01_taxes_on_delivery_cost(self):
        # Creating taxes and fiscal position

        self.env.ref('base.group_user').write({'implied_ids': [(4, self.env.ref('product.group_product_pricelist').id)]})

        tax_price_include, tax_price_exclude = self.env['account.tax'].create([{
            'name': '10% inc',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 10,
            'price_include_override': 'tax_included',
            'include_base_amount': True,
        }, {
            'name': '15% exc',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 15,
        }])

        fiscal_position = self.env['account.fiscal.position'].create({
            'name': 'fiscal_pos_a',
            'tax_ids': [
                (0, None, {
                    'tax_src_id': tax_price_include.id,
                    'tax_dest_id': tax_price_exclude.id,
                }),
            ],
        })

        # Setting tax on delivery product
        self.normal_delivery.product_id.taxes_id = tax_price_include

        # Create sales order
        # Required to see `pricelist_id` in the view
        self.env.user.groups_id += self.env.ref('product.group_product_pricelist')
        order_form = Form(self.env['sale.order'].with_context(tracking_disable=True))
        order_form.partner_id = self.partner
        order_form.fiscal_position_id = fiscal_position

        # Try adding delivery product as a normal product
        with order_form.order_line.new() as line:
            line.product_id = self.normal_delivery.product_id
            line.product_uom_qty = 1.0
        sale_order = order_form.save()

        self.assertRecordValues(sale_order.order_line, [{'price_subtotal': 9.09, 'price_total': 10.45}])

        # Now trying to add the delivery line using the delivery wizard, the results should be the same as before
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context(default_order_id=sale_order.id,
                          default_carrier_id=self.normal_delivery.id))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()

        line = sale_order.order_line.filtered_domain([
            ('product_id', '=', self.normal_delivery.product_id.id),
            ('is_delivery', '=', True),
        ])

        self.assertRecordValues(line, [{'price_subtotal': 9.09, 'price_total': 10.45}])

    def test_estimated_weight(self):
        """
        Test that negative qty SO lines are not included in the estimated weight calculation
        of delivery carriers (since it's used when calculating their rates).
        """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                }),
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': -1,
                }),
            ],
        })
        shipping_weight = sale_order._get_estimated_weight()
        self.assertEqual(shipping_weight, self.product.weight, "Only positive quantity products' weights should be included in estimated weight")

    def test_fixed_price_margins(self):
        """
         margins should be ignored for fixed price carriers
        """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'name': 'SO - fixed del',
            'order_line': [
                (0, 0, {
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                }),
            ]
        })
        self.normal_delivery.fixed_margin = 100
        self.normal_delivery.margin = 4.2
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context(default_order_id=sale_order.id,
                          default_carrier_id=self.normal_delivery.id))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()

        line = sale_order.order_line.filtered('is_delivery')
        self.assertEqual(line.price_unit, self.normal_delivery.fixed_price)

    def test_price_with_weight_volume_variable(self):
        """ Test that the price is correctly computed when the variable is weight*volume. """
        qty = 3
        list_price = 2
        volume = 2.5
        weight = 1.5
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_4.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.env['product.product'].create({
                        'name': 'wv',
                        'weight': weight,
                        'volume': volume,
                    }).id,
                    'product_uom_qty': qty,
                }),
            ],
        })
        delivery = self.env['delivery.carrier'].create({
            'name': 'Delivery Charges',
            'delivery_type': 'base_on_rule',
            'product_id': self.product_delivery_normal.id,
            'price_rule_ids': [(0, 0, {
                'variable': 'price',
                'operator': '>=',
                'max_value': 0,
                'list_price': list_price,
                'variable_factor': 'wv',
            })]
        })
        self.assertEqual(
            delivery._get_price_available(sale_order),
            qty * list_price * weight * volume,
            "The shipping price is not correctly computed with variable weight*volume.",
        )

    def test_delivery_product_taxes_on_branch(self):
        """ Check taxes populated on delivery line on branch company.
            Taxes from the branch company should be taken with a fallback on parent company.
        """
        company = self.env.company
        branch = self.env['res.company'].create({
            'name': 'Branch',
            'country_id': company.country_id.id,
            'parent_id': company.id,
        })
        # create taxes for the parent company and its branch
        tax_groups = self.env['account.tax.group'].create([{
            'name': 'Tax Group A',
            'company_id': company.id,
        }, {
            'name': 'Tax Group B',
            'company_id': branch.id,
        }])
        tax_a = self.env['account.tax'].create({
            'name': 'Tax A',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 10,
            'tax_group_id': tax_groups[0].id,
            'company_id': company.id,
        })
        tax_b = self.env['account.tax'].create({
            'name': 'Tax B',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 20,
            'tax_group_id': tax_groups[1].id,
            'company_id': branch.id,
        })
        # create delivery product with taxes from both branch and parent company
        delivery_product = self.env['product.product'].create({
            'name': 'Delivery Product',
            'taxes_id': [Command.set((tax_a + tax_b).ids)],
        })
        # create delivery
        delivery = self.env['delivery.carrier'].create({
            'name': 'Delivery Charges',
            'delivery_type': 'fixed',
            'product_id': delivery_product.id,
            'company_id': branch.id,
        })
        # create a SO from Branch
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_4.id,
            'company_id': branch.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 1,
            })],
        })
        # add delivery
        wizard = self.env['choose.delivery.carrier'].create({
            'order_id': sale_order.id,
            'carrier_id': delivery.id,
            'company_id': branch.id,
        })
        wizard.button_confirm()
        delivery_line = sale_order.order_line.filtered(lambda l: l.is_delivery)

        # delivery line should have taxes from the branch company
        self.assertRecordValues(delivery_line, [{'product_id': delivery_product.id, 'tax_id': tax_b.ids}])

        # update delivery product by setting only the tax from parent company
        delivery_product.write({'taxes_id': [Command.set((tax_a).ids)]})
        # update delivery
        wizard = self.env['choose.delivery.carrier'].create({
            'order_id': sale_order.id,
            'carrier_id': delivery.id,
            'company_id': branch.id,
        })
        wizard.button_confirm()
        delivery_line = sale_order.order_line.filtered(lambda l: l.is_delivery)

        # delivery line should have taxes from the parent company as there is no tax from the branch company
        self.assertRecordValues(delivery_line, [{'product_id': delivery_product.id, 'tax_id': tax_a.ids}])

    def test_update_weight_in_shipping_when_change_quantity(self):
        product_test = self.env['product.product'].create({
            'name': 'Test product',
            'weight': 1,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': product_test.id,
                    'product_uom_qty': 10,
                    'product_uom': self.uom_unit.id,
                }),
            ],
        })
        delivery = self.env['delivery.carrier'].create({
            'name': 'Delivery Charges',
            'delivery_type': 'base_on_rule',
            'product_id': product_test.id,
            'price_rule_ids': [
                Command.create({
                    'variable': 'weight',
                    'operator': '<=',
                    'max_value': 30,
                    'list_base_price': 5,
                    'variable_factor': 'weight',
                }),
                Command.create({
                    'variable': 'weight',
                    'operator': '>=',
                    'max_value': 60,
                    'list_base_price': 10,
                    'variable_factor': 'weight',
                })
            ]
        })

        del_form = sale_order.action_open_delivery_wizard()
        choose_delivery_carrier = self.env[del_form['res_model']].with_context(del_form['context']).create({
            'carrier_id': delivery.id,
            'order_id': sale_order.id
        })
        choose_delivery_carrier.button_confirm()
        self.assertEqual(choose_delivery_carrier.total_weight, 10)
        sale_order.order_line.write({
            'product_uom_qty': 100,
        })
        updated_del_form = sale_order.action_open_delivery_wizard()
        self.assertEqual(updated_del_form['context']['default_total_weight'], 100)

    def test_base_on_rule_currency_is_converted(self):
        """
        For based on rules delivery method without a company, check that the price
        is converted from the main's company's currency to the current company's on SOs
        """

        # Create a company that uses a different currency
        currency_bells = self.env['res.currency'].create({
            'name': 'Bell',
            'symbol': 'C',
        })

        nook_inc = self.env['res.company'].create({
            'name': 'Nook inc.',
            'currency_id': currency_bells.id,
        })

        with freeze_time('2000-01-01'):  # Make sure the rate is in the past
            self.env['res.currency.rate'].with_company(nook_inc).create({
                'currency_id': currency_bells.id,
                'company_rate': 0.5,
                'inverse_company_rate': 2,
            })

        # Company less shipping method
        product_delivery_rule = self.env['product.product'].with_company(nook_inc).create({
            'name': 'rule delivery charges',
            'type': 'service',
            'list_price': 10.0,
            'categ_id': self.env.ref('delivery.product_category_deliveries').id,
        })

        delivery = self.env['delivery.carrier'].with_company(nook_inc).create({
            'name': 'Rule Delivery',
            'delivery_type': 'base_on_rule',
            'product_id': product_delivery_rule.id,
            'price_rule_ids': [(0, 0, {
                'variable': 'price',
                'operator': '>=',
                'max_value': 0,
                'variable_factor': 'weight',
                'list_base_price': 15,
            })]
        })

        # Create sale using the shipping method
        so = self.env['sale.order'].with_company(nook_inc).create({
            'partner_id': self.partner_4.id,
            'partner_invoice_id': self.partner_4.id,
            'partner_shipping_id': self.partner_4.id,
            'order_line': [(0, 0, {
                'name': 'PC Assamble + 2GB RAM',
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'product_uom': self.uom_unit.id,
                'price_unit': 750.00,
            })],
        })

        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_company(nook_inc).with_context({
            'default_order_id': so.id,
            'default_carrier_id': delivery.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()

        # check delivery price was properly converted
        delivery_sol = so.order_line[-1]
        self.assertEqual(delivery_sol.product_id, delivery.product_id)
        self.assertEqual(delivery_sol.price_subtotal, 7.5)
