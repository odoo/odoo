# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import PartnershipCommon


@tagged('post_install', '-at_install')
class TestPartnership(PartnershipCommon):

    def test_sell_basic_partnership(self):
        self.sale_order_partnership.action_confirm()
        self.assertEqual(
            self.partner.grade_id,
            self.partnership_product.grade_id,
            "Selling the partnership should assign the grade to the partner",
        )
        self.assertEqual(
            self.partner.specific_property_product_pricelist,
            self.partnership_product.grade_id.default_pricelist_id,
            "Selling the partnership should assign the pricelist to the partner",
        )

    def test_constrains_uniqueness_partnership_grade(self):
        partnership = self.env['product.product'].create({
            'name': 'Partnership',
            'type': 'service',
            'list_price': 100.00,
            'service_tracking': 'partnership',
            'grade_id': self.env['res.partner.grade'].create({'name': 'A+'}).id,
        })
        with self.assertRaises(ValidationError):
            # A sale order cannot contain partnership products assigning different grade levels
            self.sale_order_partnership.order_line = [Command.create({'product_id': partnership.id})]

    def test_partnership_product_domain(self):
        ProductTemplate = self.env['product.template']
        product_domain = [
            ('sale_ok', '=', True),
            ('service_tracking', 'in', ProductTemplate._get_saleable_tracking_types()),
        ]
        self.assertIn(
            self.partnership_product.product_tmpl_id,
            ProductTemplate.search(product_domain),
            "Partnership product should be saleable",
        )
