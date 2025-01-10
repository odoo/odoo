from odoo.tests import tagged

from .common import TestMembershipCommon


@tagged('post_install', '-at_install')
class TestMembership(TestMembershipCommon):

    def test_sell_basic_membership(self):
        self.env['sale.order'].create({
            'partner_id': self.partner_1.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.membership_1.id,
                }),
            ],
        }).action_confirm()
        self.assertEqual(
            self.partner_1.commercial_partner_id.property_product_pricelist,
            self.membership_1.members_pricelist_id,
            "Selling the membership should assign the pricelist to the partner",
        )
        self.assertEqual(
            self.partner_1.commercial_partner_id.grade_id,
            self.membership_1.members_grade_id,
            "Selling the membership should assign the grade to the partner",
        )
