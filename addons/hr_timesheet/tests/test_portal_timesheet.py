# -*- coding: utf-8 -*-

from odoo import Command
from odoo.tests import tagged

from odoo.addons.project.tests.test_project_sharing import TestProjectSharingCommon

@tagged('post_install', '-at_install')
class TestPortalTimesheet(TestProjectSharingCommon):

    def test_ensure_fields_view_get_access(self):
        """ Ensure that the method _fields_view_get is accessible without
            raising an error for all portal users
        """
        # A portal collaborator is added to a project to enable the rule analytic.account.analytic.line.timesheet.portal.user
        self.project_portal.write({
            'collaborator_ids': [
                Command.create({'partner_id': self.user_portal.partner_id.id}),
            ],
        })
        for view in ['form', 'tree']:
            # Should not raise any access error
            self.env['account.analytic.line'].with_user(self.user_portal).fields_view_get(view_type=view)
