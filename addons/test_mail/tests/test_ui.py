# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):
    """ This tour is not imported in __init__ as the Longpolling required to update the message
        list is not available in test mode.
        see: https://github.com/odoo/odoo/commit/673f4aa4a77161dc58e0e1bf97e8f713b1e88491 """

    def test_01_project_tour(self):
        self.phantom_js("/web", "odoo.__DEBUG__.services['web_tour.tour'].run('mail_tour')", "odoo.__DEBUG__.services['web_tour.tour'].tours.mail_tour.ready", login="admin")
