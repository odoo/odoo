# -*- coding: utf-8 -*-

from odoo.tests import HttpCase, tagged

@tagged('post_install', '-at_install')
class TestProjectUpdateUi(HttpCase):

    def test_01_project_tour(self):
        self.start_tour("/odoo", 'project_update_tour', login="admin")
        self.start_tour("/odoo", 'project_tour', login="admin")
