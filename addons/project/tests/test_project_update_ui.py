# -*- coding: utf-8 -*-

from odoo.tests import HttpCase, tagged

@tagged('post_install', '-at_install')
class TestProjectUpdateUi(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Enable the "Milestones" feature to be able to create milestones on this tour.
        cls.env['res.config.settings'] \
            .create({'group_project_milestone': True}) \
            .execute()

    def test_01_project_tour(self):
        import unittest; raise unittest.SkipTest("skipWOWL")
        self.start_tour("/web", 'project_update_tour', login="admin")
