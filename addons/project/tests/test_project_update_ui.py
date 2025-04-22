# -*- coding: utf-8 -*-

from odoo.tests import HttpCase, tagged

@tagged('post_install', '-at_install')
class TestProjectUpdateUi(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Enable the "Milestones" feature to be able to create milestones on this tour.
        cls.env.ref('base.group_user').sudo().implied_ids |= cls.env.ref('project.group_project_milestone')

    def test_01_project_tour(self):
        self.start_tour("/odoo", 'project_update_tour', login="admin")
        self.start_tour("/odoo", 'project_tour', login="admin")
