# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_demo_course_tour(self):
        # remove membership because we need to be able to join the course during the tour
        self.env.ref('website_slides.slide_slide_1_0_partner_demo').unlink()
        self.env.ref('website_slides.slide_slide_1_1_partner_demo').unlink()
        self.env.ref('website_slides.slide_channel_1_partner_demo').unlink()

        self.phantom_js('/slides', "odoo.__DEBUG__.services['web_tour.tour'].run('course_tour')", "odoo.__DEBUG__.services['web_tour.tour'].tours.course_tour.ready", login="demo")
