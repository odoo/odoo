# -*- coding: utf-8 -*-

from openerp.addons.website_forum.tests.common import TestForumCommon


class TestForumSEOCommon(TestForumCommon):
    def setUp(self):
        super(TestForumCommon, self).setUp()

        # Test users
        TestUsersEnv = self.env['res.users'].with_context({'no_reset_password': True})
        group_marketing_manager_id = self.ref('marketing.group_marketing_manager')
        group_erp_manager = self.ref('base.group_erp_manager')

        self.user_marketing_manager = TestUsersEnv.create({
            'name': 'Durandal MarketingManager',
            'login': 'Durandal',
            'alias_name': 'durandal',
            'email': 'durandal.marketing_manager@example.com',
            'karma': 0,
            'groups_id': [(6, 0, [group_marketing_manager_id])]
        })
        self.user_erp_manager = TestUsersEnv.create({
            'name': 'Cedric Public',
            'login': 'Cedric',
            'alias_name': 'cedric',
            'email': 'cedric.employee@example.com',
            'karma': 0,
            'groups_id': [(6, 0, [group_erp_manager])]
        })

        # delete existing seo words
        self.env['forum.seo'].search([]).unlink()
