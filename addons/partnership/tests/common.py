# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.product.tests.common import ProductCommon


class PartnershipCommon(ProductCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.pricelist = cls._enable_pricelists()
        cls.partner_grade = cls.env['res.partner.grade'].create({
            'name': 'Unicorn',
            'default_pricelist_id': cls.pricelist.id,
        })
        cls.partnership_product = cls.env['product.product'].create({
            'name': 'Basic Limited',
            'type': 'service',
            'list_price': 100.00,
            'service_tracking': 'partnership',
            'grade_id': cls.partner_grade.id,
        })
        # SETUP master-data created as the independent admin in setUpClass.
        # sudo the create and own it by the restricted test_user so that the
        # sale.order personal-orders ir.rule (sales_team.group_sale_salesman)
        # lets the test methods read/write/confirm it.
        cls.sale_order_partnership = cls.env['sale.order'].sudo().create({
            'partner_id': cls.partner.id,
            'user_id': cls._test_user.id if cls._test_user else cls.env.user.id,
            'order_line': [Command.create({'product_id': cls.partnership_product.id})],
        })
