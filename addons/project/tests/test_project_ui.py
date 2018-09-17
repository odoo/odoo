# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_project_tour(self):
        self.phantom_js("/web", "odoo.__DEBUG__.services['web_tour.tour'].run('project_tour')", "odoo.__DEBUG__.services['web_tour.tour'].tours.project_tour.ready", login="admin")
    
    def test_02_project_portal_tour_admin(self):
        self.phantom_js("/web", "odoo.__DEBUG__.services['web_tour.tour'].run('portal_project_tour_admin')",
                        "odoo.__DEBUG__.services['web_tour.tour'].tours.portal_project_tour_admin.ready",
                        login="admin", timeout=180)
    
    # def test_03_project_portal_tour_unlogged_accesstoken(self):
    #     self.phantom_js("/web", "odoo.__DEBUG__.services['web_tour.tour'].run('portal_project_tour_unlogged_accesstoken')",
    #                     "odoo.__DEBUG__.services['web_tour.tour'].tours.portal_project_tour_unlogged_accesstoken.ready",
    #                     login=None, timeout=180)
