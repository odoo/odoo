# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_demo_course_purchase_tour(self):
        self.phantom_js('/slides', "odoo.__DEBUG__.services['web_tour.tour'].run('course_purchase_tour')", "odoo.__DEBUG__.services['web_tour.tour'].tours.course_purchase_tour.ready", login="demo")
