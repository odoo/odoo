# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import fields
from odoo.tests import HttpCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestEventProductConfiguratorUi(AccountTestInvoicingCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.group_ids += cls.quick_ref('event.group_event_manager')

        # Adding sale users to test the access rights
        cls.salesman = mail_new_test_user(
            cls.env,
            name='Salesman',
            login='salesman',
            password='salesman',
            groups='sales_team.group_sale_salesman',
        )

        # Setup partner since user salesman don't have the right to create it on the fly
        cls.env['res.partner'].create({'name': 'Tajine Saucisse'})

        # Setup attributes and attributes values
        product_attribute_age = cls.env['product.attribute'].create({
            'name': 'Age',
            'sequence': 10,
        })
        product_attribute_value_0 = cls.env['product.attribute.value'].create({
            'name': 'Kid',
            'attribute_id': product_attribute_age.id,
            'sequence': 1,
        })
        product_attribute_value_1 = cls.env['product.attribute.value'].create({
            'name': 'Adult',
            'attribute_id': product_attribute_age.id,
            'sequence': 2,
        })
        product_attribute_value_2 = cls.env['product.attribute.value'].create({
            'name': 'Senior',
            'attribute_id': product_attribute_age.id,
            'sequence': 3,
        })
        product_attribute_value_3 = cls.env['product.attribute.value'].create({
            'name': 'VIP',
            'attribute_id': product_attribute_age.id,
            'sequence': 3,
        })

        # Create product template
        cls.event_product_template = cls.env['product.template'].create({
            'name': 'Registration Event (TEST variants)',
            'list_price': 30.0,
            'type': 'service',
            'service_tracking': 'event',
        })

        # Generate variants
        cls.env['product.template.attribute.line'].create([{
            'product_tmpl_id': cls.event_product_template.id,
            'attribute_id': product_attribute_age.id,
            'value_ids': [
                (4, product_attribute_value_0.id),
                (4, product_attribute_value_1.id),
                (4, product_attribute_value_2.id),
                (4, product_attribute_value_3.id),
            ],
        }])

        # Apply a price_extra for the attributes
        cls.event_product_template.attribute_line_ids[0].product_template_value_ids[0]. \
            price_extra = -20.00
        cls.event_product_template.attribute_line_ids[0].product_template_value_ids[2]. \
            price_extra = -10.00
        cls.event_product_template.attribute_line_ids[0].product_template_value_ids[3]. \
            price_extra = 30.00

        # Create the event and link it to the product variants as event tickets
        cls.event = cls.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'date_tz': 'Europe/Brussels',
        })

        for variant in cls.event_product_template.attribute_line_ids[0].product_template_value_ids:
            cls.env['event.event.ticket'].create({
                'name': variant.name,
                'event_id': cls.event.id,
                'product_id': variant.ptav_product_variant_ids[0].id,
            })
            if variant.name != 'VIP':
                cls.env['event.event.ticket'].create({
                    'name': variant.name + ' + meal',
                    'event_id': cls.event.id,
                    'product_id': variant.ptav_product_variant_ids[0].id,
                    'price': variant.ptav_product_variant_ids[0].lst_price + 5,
                })

            # Adding an optional product
            cls.product_product_memorabilia = cls.env['product.template'].create({
                'name': 'Memorabilia (TEST)',
                'list_price': 16.50,
            })

            cls.event_product_template.optional_product_ids = [cls.product_product_memorabilia.id,]

    def test_event_using_product_configurator(self):
        self.start_tour("/odoo", 'event_sale_with_product_configurator_tour', login='salesman')

        sale_order = self.env['sale.order'].search([('create_uid', "=", self.salesman.id)])

        # Check that all the so lines are in the so and that the total amount is correct
        self.assertEqual(len(sale_order.order_line), 4)
        self.assertEqual(sale_order.amount_total, 277.73)
