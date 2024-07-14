# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.tests import HttpCase, tagged, loaded_demo_data
from odoo.addons.mail.tests.common import mail_new_test_user

_logger = logging.getLogger(__name__)


@tagged('-at_install', 'post_install')
class ProjectEnterpriseTestUi(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        user_groups = 'base.group_user,project.group_project_manager'
        if 'account.move.line' in cls.env:
            user_groups += ',account.group_account_invoice'
        cls.user_project_manager = mail_new_test_user(
            cls.env,
            company_id=cls.env.company.id,
            email='gilbert.testuser@test.example.com',
            login='user_project_manager',
            groups=user_groups,
            name='Gilbert ProjectManager',
            tz='Europe/Brussels',
        )

    def test_01_ui(self):
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
        self.start_tour("/", 'project_test_tour', login='admin')
