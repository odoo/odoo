# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from unittest.mock import patch
from odoo.osv import expression

@odoo.tests.tagged('post_install', '-at_install')
class TestWebsiteProjectForm(odoo.tests.HttpCase):
    def test_no_project_error_tour(self):
        Project = self.env['project.project']
        Project_search = type(Project).search_fetch
        existing_project_ids = Project._search([])

        def fake_project_search_fetch(self, domain, fieldnames, offset=0, limit=None, order=None):
            return Project_search(
                self,
                expression.AND([
                    domain,
                    [('id', 'not in', list(existing_project_ids))],
                ]),
                fieldnames, offset, limit, order
            )

        # It is necessary to run the tours like these because they require the absence of projects
        # but demo-data projects are automatically created
        with patch.object(type(Project), 'search_fetch', fake_project_search_fetch):
            # The first tour tests whether the pop-up is raised in the absence of projects
            self.start_tour(self.env['website'].get_client_action_url('/contactus'), 'website_form_no_project_tour', login='admin')

            # The second tour tests whether the pop-up is not shown when a project exists
            self.env['project.project'].create({
                'name': 'test project',
            })
            current_projects = self.env['project.project'].search([])
            self.assertEqual(len(list(current_projects)), 1)
            self.start_tour('/contactus', 'website_form_error_create_project', login='admin')
