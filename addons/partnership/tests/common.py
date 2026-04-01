# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.product.tests.common import ProductCommon


class PartnershipCommon(ProductCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

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
        cls.sale_order_partnership = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'order_line': [Command.create({'product_id': cls.partnership_product.id})],
        })
