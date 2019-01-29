# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tests


@tests.common.tagged('post_install', '-at_install')
class TestSlidesFrontend(tests.HttpCase):

    def test_tour_slides_admin(self):
        self.phantom_js(
            "/slides",
            "odoo.__DEBUG__.services['web_tour.tour'].run('tour_slides')",
            "odoo.__DEBUG__.services['web_tour.tour'].tours.tour_slides.ready",
            login="admin"
        )
