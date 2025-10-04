# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.config.settings'].create({'group_project_milestone': True}).execute()

    def test_01_project_tour(self):
        self.start_tour("/web", 'project_tour', login="admin")
