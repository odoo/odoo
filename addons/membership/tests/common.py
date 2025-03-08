from odoo.addons.product.tests.common import ProductCommon


class TestMembershipCommon(ProductCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Test memberships
        cls.membership_1 = cls.env['product.product'].create({
            'name': 'Basic Limited',
            'type': 'service',
            'list_price': 100.00,
            'service_tracking': 'membership',
            'members_grade_id': cls.env.ref('membership.res_partner_grade_data_gold').id,
            'members_pricelist_id': cls.pricelist.id,
        })

        # Test people
        cls.partner_1 = cls.env['res.partner'].create({
            'name': 'Ignasse Reblochon',
        })
        cls.partner_2 = cls.env['res.partner'].create({
            'name': 'Martine Poulichette',
        })
