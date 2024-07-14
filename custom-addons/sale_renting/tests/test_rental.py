# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.fields import Command
from odoo.tools import float_compare
from odoo.tests import HttpCase, tagged, TransactionCase


class TestRentalCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.country_id = cls.env.ref('base.us')
        cls.env['account.tax.group'].create(
            {'name': 'Test Account Tax Group', 'company_id': cls.env.company.id}
        )

        cls.product_id = cls.env['product.product'].create({
            'name': 'Projector',
            'categ_id': cls.env.ref('product.product_category_all').id,
            'type': 'consu',
            'rent_ok': True,
            'extra_hourly': 7.0,
            'extra_daily': 30.0,
        })

        cls.product_template_id = cls.product_id.product_tmpl_id

        cls.product_template_id.product_pricing_ids.unlink()
        cls.recurrence_hourly = cls.env['sale.temporal.recurrence'].create({'duration': 1.0, 'unit': 'hour'})
        cls.recurrence_5_hours = cls.env['sale.temporal.recurrence'].create({'duration': 5.0, 'unit': 'hour'})
        cls.recurrence_15_hours = cls.env['sale.temporal.recurrence'].create({'duration': 15.0, 'unit': 'hour'})
        cls.recurrence_daily = cls.env['sale.temporal.recurrence'].create({'duration': 1.0, 'unit': 'day'})
        # blank the demo pricings

        PRICINGS = [
            {
                'recurrence_id': cls.recurrence_hourly.id,
                'price': 3.5,
            }, {
                'recurrence_id': cls.recurrence_5_hours.id,
                'price': 15.0,
            }, {
                'recurrence_id': cls.recurrence_15_hours.id,
                'price': 40.0,
            }, {
                'recurrence_id': cls.recurrence_daily.id,
                'price': 60.0,
            },
        ]

        for pricing in PRICINGS:
            pricing.update(product_template_id=cls.product_template_id.id)
            cls.env['product.pricing'].create(pricing)

        cls.tax_included = cls.env['account.tax'].create({'name': 'Tax Incl', 'amount': 10, 'price_include': True})
        cls.tax_excluded = cls.env['account.tax'].create({'name': 'Tax Excl', 'amount': 10, 'price_include': False})

    def test_pricing(self):
        # check pricing returned = expected
        now = fields.Datetime.now()
        self.assertEqual(
            self.product_id._get_best_pricing_rule(
                start_date=now, end_date=now + relativedelta(hours=9)
            )._compute_price(9.0, 'hour'),
            30.0,
        )

        self.assertEqual(
            self.product_id._get_best_pricing_rule(
                start_date=now, end_date=now + relativedelta(hours=1)
            )._compute_price(11.0, 'hour'),
            38.5,
        )

        self.assertEqual(
            self.product_id._get_best_pricing_rule(
                start_date=now, end_date=now + relativedelta(hours=16)
            )._compute_price(16.0, 'hour'),
            56.0,
        )

        self.assertEqual(
            self.product_id._get_best_pricing_rule(
                start_date=now, end_date=now + relativedelta(hours=20)
            )._compute_price(20.0, 'hour'),
            60.0,
        )

        self.assertEqual(
            self.product_id._get_best_pricing_rule(
                start_date=now, end_date=now + relativedelta(hours=24)
            )._compute_price(24.0, 'hour'),
            60.0,
        )

    def test_pricing_advanced(self):
        # with pricings applied only to some variants ...
        return

    def test_pricelists(self):
        partner = self.env['res.partner'].create({'name': 'A partner'})
        pricelist_A = self.env['product.pricelist'].create({
            'name': 'Pricelist A',
        })
        pricelist_B = self.env['product.pricelist'].create({
            'name': 'Pricelist B',
        })

        PRICINGS = [
            {
                'recurrence_id': self.recurrence_hourly.id,
                'price': 3.5,
                'pricelist_id': pricelist_A.id,
            }, {
                'recurrence_id': self.recurrence_5_hours.id,
                'price': 15.0,
                'pricelist_id': pricelist_B.id,
            }
        ]
        self.product_template_id.list_price = 42
        self.product_template_id.product_pricing_ids.unlink()
        for pricing in PRICINGS:
            pricing.update(product_template_id=self.product_template_id.id)
            pricing = self.env['product.pricing'].create(pricing)

        reservation_begin = fields.Datetime.now()
        pickup_date = reservation_begin + relativedelta(days=1)
        return_date = pickup_date + relativedelta(hours=1)

        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'rental_start_date': pickup_date,
            'rental_return_date': return_date,
        })

        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'order_id': sale_order.id,
            'reservation_begin': reservation_begin,
        })
        sol.update({'is_rental': True})

        sale_order.write({'pricelist_id': pricelist_A.id})
        sale_order._recompute_prices()
        self.assertEqual(sol.price_unit, 3.5, "Pricing should take into account pricelist A")
        sale_order.write({'pricelist_id': pricelist_B.id})
        sale_order._recompute_prices()
        self.assertEqual(sol.price_unit, 15, "Pricing should take into account pricelist B")

    def test_delay_pricing(self):
        # Return Products late and verify duration is correct.
        self.product_id.extra_hourly = 2.5
        self.product_id.extra_daily = 15.0

        self.assertEqual(
            self.product_id._compute_delay_price(timedelta(hours=5.0)),
            12.5
        )

        self.assertEqual(
            self.product_id._compute_delay_price(timedelta(hours=5.0, days=6)),
            102.5
        )

    def test_discount(self):
        partner = self.env['res.partner'].create({'name': 'A partner'})
        pricelist_A = self.env['product.pricelist'].create({
            'name': 'Pricelist A',
            'discount_policy': 'without_discount',
            'company_id': self.env.company.id,
            'item_ids': [(0, 0, {
                'applied_on': '3_global',
                'compute_price': 'percentage',
                'percent_price': 10,
            })],
        })
        pricelist_B = self.env['product.pricelist'].create({
            'name': 'Pricelist B',
            'discount_policy': 'without_discount',
            'company_id': self.env.company.id,
            'item_ids': [(0, 0, {
                'applied_on': '3_global',
                'compute_price': 'percentage',
                'percent_price': 20,
            })],
        })

        PRICINGS = [
            {
                'recurrence_id': self.recurrence_hourly.id,
                'price': 3.5,
                'pricelist_id': pricelist_A.id,
            }, {
                'recurrence_id': self.recurrence_5_hours.id,
                'price': 15.0,
                'pricelist_id': pricelist_B.id,
            }
        ]
        self.product_template_id.product_pricing_ids.unlink()
        for pricing in PRICINGS:
            pricing.update(product_template_id=self.product_template_id.id)
            pricing = self.env['product.pricing'].create(pricing)

        reservation_begin = fields.Datetime.now()
        pickup_date = reservation_begin + relativedelta(days=1)
        return_date = pickup_date + relativedelta(hours=1)

        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'rental_start_date': pickup_date,
            'rental_return_date': return_date,
        })

        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'product_uom_qty': 1,
            'order_id': sale_order.id,
            'reservation_begin': reservation_begin,
        })
        sol.update({'is_rental': True})
        sale_order.write({'pricelist_id': pricelist_A.id})
        sale_order._recompute_prices()
        self.assertEqual(sol.discount, 0, "Discount should always been 0 on pricelist change")
        sale_order.write({'pricelist_id': pricelist_B.id})
        sale_order._recompute_prices()
        self.assertEqual(sol.discount, 0, "Discount should always been 0 on pricelist change")

    # TODO availability testing with sale_rental functions? (no stock)

    def test_no_pickup_nor_return(self):
        partner = self.env['res.partner'].create({'name': 'A partner'})

        recurrence_hour = self.env['sale.temporal.recurrence'].create({'duration': 1.0, 'unit': 'hour'})
        PRICINGS = [
            {
                'recurrence_id': recurrence_hour.id,
                'price': 3.5,
            }
        ]
        self.product_template_id.product_pricing_ids.unlink()
        for pricing in PRICINGS:
            pricing.update(product_template_id=self.product_template_id.id)
            pricing = self.env['product.pricing'].create(pricing)

        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
        })
        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'order_id': sale_order.id,
        })

        self.assertEqual(sol.price_unit, 1, "No pricing should be taken into account if no pickup nor return date.")
        sale_order._recompute_prices()
        self.assertEqual(sol.price_unit, 1, "Update price should not alter first computed price.")

    def test_no_price_update_on_pickup_return_update(self):
        partner = self.env['res.partner'].create({'name': 'A partner'})

        recurrence_hour = self.env['sale.temporal.recurrence'].create({'duration': 1.0, 'unit': 'hour'})
        PRICINGS = [
            {
                'recurrence_id': recurrence_hour.id,
                'price': 3.5,
            }
        ]
        self.product_template_id.product_pricing_ids.unlink()
        for pricing in PRICINGS:
            pricing.update(product_template_id=self.product_template_id.id)
            pricing = self.env['product.pricing'].create(pricing)

        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
        })
        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'order_id': sale_order.id,
        })

        self.assertEqual(sol.price_unit, 1, "No pricing should be taken into account if no pickup nor return date.")
        sale_order.write({
            'rental_start_date': fields.Datetime.now() + relativedelta(days=1),
            'rental_return_date': fields.Datetime.now() + relativedelta(days=1, hours=1),
        })
        sol.write({'is_rental': True})
        self.assertEqual(sol.price_unit, 1, "Update price should not alter first computed price.")
        sale_order._recompute_prices()
        self.assertEqual(sol.price_unit, 3.5, "Update price should recompute the price.")

    def test_no_pricing_for_pricelist(self):
        pricelist_A = self.env['product.pricelist'].create({
            'name': 'Pricelist A',
        })
        pricelist_B = self.env['product.pricelist'].create({
            'name': 'Pricelist B',
        })
        partner = self.env['res.partner'].create(
            {'name': 'A partner', 'property_product_pricelist': pricelist_B}
        )
        recurrence_hour = self.env['sale.temporal.recurrence'].create({'duration': 1.0, 'unit': 'hour'})
        PRICINGS = [
            {
                'recurrence_id': recurrence_hour.id,
                'price': 3.5,
                'pricelist_id': pricelist_A.id,
            }
        ]
        self.product_template_id.product_pricing_ids.unlink()
        for pricing in PRICINGS:
            pricing.update(product_template_id=self.product_template_id.id)
            self.env['product.pricing'].create(pricing)

        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'rental_start_date': fields.Datetime.now() + relativedelta(days=1),
            'rental_return_date': fields.Datetime.now() + relativedelta(days=1, hours=1),
        })
        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'order_id': sale_order.id,
        })
        sol.update({'is_rental': True})

        self.assertEqual(sol.price_unit, 1, "No pricing should be taken into account if no pricing corresponds to a given pricelist.")

    def test_contextual_price_is_pickup_return_dependant(self):
        pricelist_A = self.env['product.pricelist'].create({
            'name': 'Pricelist A',
        })
        recurrence_hour = self.env['sale.temporal.recurrence'].create({'duration': 1.0, 'unit': 'hour'})
        PRICINGS = [
            {
                'recurrence_id': recurrence_hour.id,
                'price': 3.5,
            }
        ]
        self.product_template_id.product_pricing_ids.unlink()
        for pricing in PRICINGS:
            pricing.update(product_template_id=self.product_template_id.id)
            pricing = self.env['product.pricing'].create(pricing)

        price = self.product_template_id.with_context(
            start_date=fields.Datetime.now() + relativedelta(days=1),
            end_date=fields.Datetime.now() + relativedelta(days=1, hours=2),
            pricelist=pricelist_A.id
        )._get_contextual_price()
        self.assertEqual(price, 7, "Contextual price should take pickup and return date into account")

    def test_discount_on_sol_remains(self):
        # Add group 'Discount on Lines' to the user
        self.env.user.write({'groups_id': [(4, self.env.ref('product.group_discount_per_so_line').id)]})

        now = fields.date.today()
        one_day_later = now + relativedelta(days=1)
        discount = 10

        partner = self.env['res.partner'].create({'name': 'A partner'})
        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'rental_start_date': now,
            'rental_return_date': one_day_later,
        })

        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'product_uom_qty': 1,
            'price_unit': 10,
            'order_id': sale_order.id,
            'reservation_begin': now,
            'discount': discount,
        })
        sol.update({'is_rental': True})

        self.assertEqual(sol.discount, discount, 'Discount should not be updated')
        sale_order.action_confirm()
        self.assertEqual(sol.discount, discount, 'Discount should not be updated')
        action_dict = sale_order.action_open_pickup()
        pickup_wizard = self.env['rental.order.wizard'].with_context(
            action_dict['context']
        ).create({})
        pickup_wizard._get_wizard_lines()
        pickup_wizard.apply()
        self.assertEqual(sol.discount, discount, 'Discount should not be updated')

    def test_renting_taxes_inc2ex(self):

        fiscal_position_inc2ex = self.env['account.fiscal.position'].create({'name': 'inc2ex'})
        self.env['account.fiscal.position.tax'].create({
            'position_id': fiscal_position_inc2ex.id,
            'tax_src_id': self.tax_included.id,
            'tax_dest_id': self.tax_excluded.id
        })
        self.product_id.taxes_id = self.tax_included

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'A partner'}).id,
            'fiscal_position_id': fiscal_position_inc2ex.id
        })

        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'order_id': sale_order.id,
        })
        sol.update({'is_rental': True})
        sale_order._rental_set_dates()  # not triggered automatically here

        self.assertEqual(sale_order.duration_days, 1, 'Default duration should be one day')
        self.assertEqual(sale_order.remaining_hours, 0, 'Default duration should be one day')

        self.assertTrue(
            float_compare(sol.price_total, 60/1.1, precision_rounding=2),
            "Price with 10% taxes should be equal to basic pricing"
        )

    def test_renting_taxes_ex2inc(self):
        fiscal_position_ex2inc = self.env['account.fiscal.position'].create({'name': 'ex2inc'})
        self.env['account.fiscal.position.tax'].create({
            'position_id': fiscal_position_ex2inc.id,
            'tax_src_id': self.tax_excluded.id,
            'tax_dest_id': self.tax_included.id
        })
        self.product_id.taxes_id = self.tax_excluded

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'A partner'}).id,
            'fiscal_position_id': fiscal_position_ex2inc.id
        })

        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'order_id': sale_order.id,
        })

        self.assertTrue(
            float_compare(sol.price_unit, 60*1.1, precision_rounding=2),
            "Price with included taxes should be equal to basic pricing(tax excluded) + 10% taxes"
        )

    def test_renting_taxes_included(self):
        self.product_id.taxes_id = self.tax_included

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'A partner'}).id,
        })

        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'order_id': sale_order.id,
        })

        self.assertTrue(
            float_compare(sol.price_unit, 60*1.1, precision_rounding=2),
            "unit price should be equal to basic pricing + 10% (tax included)"
        )

    def test_renting_taxes_excluded(self):
        self.product_id.taxes_id = self.tax_excluded

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'A partner'}).id,
        })

        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'order_id': sale_order.id,
        })

        self.assertTrue(
            float_compare(sol.price_unit, 60, precision_rounding=2),
            "Unit price should be equal to basic pricing (without tax excluded)"
        )

    def test_renting_taxes_ex_inc(self):
        self.product_id.taxes_id = self.tax_excluded + self.tax_included

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'A partner'}).id,
        })

        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'order_id': sale_order.id,
        })

        self.assertTrue(
            float_compare(sol.price_unit, 60*1.1, precision_rounding=2),
            "Price in wizard should be equal to basic pricing + 10% (tax included)"
        )

    def test_renting_taxes_included_multicompany(self):

        company2 = self.env['res.company'].create({'name': 'Company 2'})
        self.tax_included.company_id = company2

        self.product_id.taxes_id = self.tax_included

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'A partner'}).id,
        })

        sol = self.env['sale.order.line'].create({
            'product_id': self.product_id.id,
            'order_id': sale_order.id,
        })

        self.assertTrue(
            float_compare(sol.price_unit, 60, precision_rounding=2),
            "Included tax related to another company should not apply"
        )

    def test_non_rental_line_does_not_change_description(self):
        water_bottle = self.env["product.product"].create({
            "name": "Water Bottle",
        })
        will_smith = self.env["res.partner"].create({
            "name": "Will Smith",
        })

        now = fields.Datetime.now()
        order = self.env["sale.order"].create({
            "partner_id": will_smith.id,
            "rental_start_date": now,
            "rental_return_date": now + timedelta(days=2),
            "order_line": [
                Command.create({
                    "product_id": self.product_id.id,
                }),
                Command.create({
                    "product_id": water_bottle.id
                })
            ]
        })
        rental_order_line, non_rental_order_line = order.order_line
        rental_order_line.is_rental = True
        self.assertTrue(order.is_rental_order)

        non_rental_order_line.name = "My Water Bottle"

        # Trigger order line name recompute by changing rental field.
        order.rental_start_date = now + timedelta(days=1)

        # Non-rental order line names aren't recomputed.
        self.assertEqual(non_rental_order_line.name, "My Water Bottle")

    def test_copy_product_variant_pricings(self):
        """Check that product variants on product pricings after copying
        a product template.
        """
        product = self.product_template_id.with_context(create_product_product=True)
        product.product_pricing_ids.unlink()
        product_attribute = self.env['product.attribute'].create({
            'name': 'Color',
            'value_ids': [Command.create({'name': name}) for name in ('Blue', 'Red')],
        })
        product.attribute_line_ids = 2 * [Command.create({
            'attribute_id': product_attribute.id,
            'value_ids': product_attribute.value_ids.ids,
        })]
        for i, variant in enumerate(product.product_variant_ids, start=1):
            self.env['product.pricing'].create([{
                'product_template_id': product.id,
                'product_variant_ids': [Command.link(variant.id)],
                'recurrence_id': self.recurrence_hourly.id,
                'price': 10.0 * i,
                'pricelist_id': self.env['product.pricelist'].create({'name': f"list {i}"}).id,
            }, {
                'product_template_id': product.id,
                'product_variant_ids': [Command.link(variant.id)],
                'recurrence_id': self.recurrence_daily.id,
                'price': 25.0 * i,
           }])
        pricings_1 = product.product_pricing_ids.sorted()
        pricings_2 = product.copy().product_pricing_ids.sorted()
        self.assertEqual(
            len(pricings_2),
            8,  # 2 attributes * 2 values * 2 plans = 8 pricings
            "copied product should get 8 pricings",
        )
        self.assertNotEqual(
            pricings_2.product_variant_ids,
            pricings_1.product_variant_ids,
            "copied pricings shouldn't be linked to the original products",
        )
        for pricing_1, pricing_2 in zip(pricings_1, pricings_2):
            self.assertEqual(pricing_2.price, pricing_1.price)
            self.assertEqual(pricing_2.recurrence_id, pricing_1.recurrence_id)
            self.assertEqual(pricing_2.pricelist_id, pricing_1.pricelist_id)


@tagged('post_install', '-at_install')
class TestUi(HttpCase):

    def test_rental_flow(self):
        # somehow, the name_create and onchange of the partner_id
        # in a quotation trigger a re-rendering that loses
        # the focus of some fields, preventing the tour to
        # run successfully if a partner is created during the flow
        # create it in advance here instead
        self.env['res.partner'].name_create('Agrolait')
        self.start_tour("/web", 'rental_tour', login="admin")
