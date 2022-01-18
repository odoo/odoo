# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .test_project_base import TestProjectCommon

class TestProjectVisibility(TestProjectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.projects = cls.env['project.project']
        cls.user_tony = cls.env['res.users'].create({
            'name': 'Tony Stark',
            'login': 'tony@test.com',
            'email': 'tony@test.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])]
        })

    def test_private_project_visibility(self):
        self.project_pigs.write({'privacy_visibility': 'followers'})
        # private project should not be visible to internal user
        self.assertNotIn(self.project_pigs, self.projects.with_user(self.user_projectuser).search([]))
        # private project should be visible to internal user if user is follower of the project
        self.project_pigs.message_subscribe(partner_ids=[self.user_projectuser.partner_id.id])
        self.assertIn(self.project_pigs, self.projects.with_user(self.user_projectuser).search([]))
        self.assertNotIn(self.project_pigs, self.projects.with_user(self.user_tony).search([]))
        # private project should not be visible to portal user
        self.assertNotIn(self.project_pigs, self.projects.with_user(self.user_portal).search([]))

    def test_internal_project_visibility(self):
        self.project_pigs.write({'privacy_visibility': 'employees'})
        # Project should be visible to all the employees
        self.assertIn(self.project_pigs, self.projects.with_user(self.user_projectuser).search([]))
        self.assertIn(self.project_pigs, self.projects.with_user(self.user_tony).search([]))
        self.assertIn(self.project_pigs, self.projects.with_user(self.user_projectmanager).search([]))
        # Project should not be visible to portal user
        self.assertNotIn(self.project_pigs, self.projects.with_user(self.user_portal).search([]))

    def test_portal_project_visibilty(self):
        self.project_pigs.write({'privacy_visibility': 'portal'})
        # Project should not be visible to portal user if user is not follower of the project
        self.assertNotIn(self.project_pigs, self.projects.with_user(self.user_portal).search([]))
        # Project should be visible to all the employees
        self.assertIn(self.project_pigs, self.projects.with_user(self.user_projectuser).search([]))
        self.assertIn(self.project_pigs, self.projects.with_user(self.user_tony).search([]))
        # Project should be visible to portal user if user is follower of the project
        self.project_pigs.message_subscribe(partner_ids=[self.user_portal.partner_id.id])
        self.assertIn(self.project_pigs, self.projects.with_user(self.user_portal).search([]))
