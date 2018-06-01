# -*- coding: utf-8 -*-

from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tools.datetime import date


class TestMembershipCommon(AccountingTestCase):

    def setUp(self):
        super(TestMembershipCommon, self).setUp()

        # Usefull models
        Partner = self.env['res.partner']

        # Test memberships
        self.membership_1 = self.env['product.product'].create({
            'membership': True,
            'membership_date_from': date.today().add(days=-2),
            'membership_date_to': date.today().add(months=1),
            'name': 'Basic Limited',
            'type': 'service',
            'list_price': 100.00,
        })

        # Test people
        self.partner_1 = Partner.create({
            'name': 'Ignasse Reblochon',
        })
        self.partner_2 = Partner.create({
            'name': 'Martine Poulichette',
            'free_member': True,
        })
