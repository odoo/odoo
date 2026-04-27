# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.tests.common import tagged

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.product_matrix.tests.common import TestMatrixCommon
from odoo.addons.sale.tests.product_configurator_common import TestProductConfiguratorCommon

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestRentalProductConfigUi(TestMatrixCommon, TestProductConfiguratorCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

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

        # Setup currency
        cls.env['res.currency'].search([('name', '!=', 'USD')]).with_context(force_deactivate=True).action_archive()
        cls.currency = cls.env['res.currency'].search([('name', '=', 'USD')])
        cls.currency.action_unarchive()

        # Update the product template that can be sold and rented
        cls.product_product_custo_desk.update({'rent_ok': True})
        recurrence_day = cls.recurrence_week = cls.env['sale.temporal.recurrence'].create({'duration': 1, 'unit': 'day'})
        # Add rental pricing
        cls.env['product.pricing'].create({
            'recurrence_id': recurrence_day.id,
            'price': 60.0,
            'product_template_id': cls.product_product_custo_desk.id
        })

        # Add a different rental pricing for in variant
        ptav = cls.env['product.template.attribute.value'].search([
            ('product_tmpl_id', '=', cls.product_product_custo_desk.id),
            '|', ('name', '=', 'White'), ('name', '=', 'Aluminium'),
        ])
        variant_desk_alu_white = cls.product_product_custo_desk._get_variant_for_combination(ptav)
        cls.env['product.pricing'].create({
            'recurrence_id': recurrence_day.id,
            # FIXME edm: right now, only work with a variant cheaper than the normal price,
            #            otherwise this pricing is ignored
            'price': 25.0,
            'product_template_id': cls.product_product_custo_desk.id,
            'product_variant_ids': [(4, variant_desk_alu_white.id),],
        })

        # Create another rental product but without variant
        cls.rental_projector_id = cls.env['product.template'].create({
            'name': 'Projector (TEST)',
            'rent_ok': True,
            'extra_hourly': 7.0,
            'extra_daily': 30.0,
        })

        # Set the rental pricing
        cls.env['product.pricing'].create({
            'recurrence_id': recurrence_day.id,
            'price': 20.0,
            'product_template_id': cls.rental_projector_id.id,
        })

    def test_rental_product_configurator(self):
        self.start_tour("/odoo", 'rental_product_configurator_tour', login='salesman')

        rental_order = self.env['sale.order'].search([('create_uid', "=", self.salesman.id)])

        self.assertTrue(rental_order.is_rental_order)
        # Check that all the products are in the order, at the rental price if rental product:
            # 2 custom desks (25/day each) => rental
            # 5 custom desks (60/day each) => rental
            # 1 Chair  => sale
            # 1 Floor protection => sale
        self.assertEqual(len(rental_order.order_line), 4)
        # We use the untaxed amount as we do not setup specific taxation during this test.
        self.assertEqual(rental_order.amount_untaxed, 412.5)
