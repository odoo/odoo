# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common
from odoo.tests.common import new_test_user


class TestUTMCommon(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestUTMCommon, cls).setUpClass()

        cls.utm_campaign = cls.env['utm.campaign'].create({'name': 'Test Campaign'})
        cls.utm_medium = cls.env['utm.medium'].create({'name': 'Test Medium'})
        cls.utm_source = cls.env['utm.source'].create({'name': 'Test Source'})

        cls.user_employee = new_test_user(cls.env, **{
            'name': 'User Employee',
            'login': 'user_employee_utm',
            'email': 'user_employee_utm@test.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
