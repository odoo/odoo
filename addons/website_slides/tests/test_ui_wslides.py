# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tests


@tests.common.tagged('post_install', '-at_install')
class TestUi(tests.HttpCase):

    def test_course_member_employee(self):
        # remove membership because we need to be able to join the course during the tour
        user_demo = self.env.ref('base.user_demo')
        user_demo.flush()
        user_demo.write({
            'groups_id': [(5, 0), (4, self.env.ref('base.group_user').id)]
        })
        self.env.ref('website_slides.slide_channel_demo_0_gard_0')._remove_membership(self.env.ref('base.partner_demo').ids)

        self.phantom_js(
            '/slides',
            'odoo.__DEBUG__.services["web_tour.tour"].run("course_member")',
            'odoo.__DEBUG__.services["web_tour.tour"].tours.course_member.ready',
            login=user_demo.login)

    def test_course_member_website_publisher(self):
        # remove membership because we need to be able to join the course during the tour
        # group_website_designer
        user_demo = self.env.ref('base.user_demo')
        user_demo.flush()
        user_demo.write({
            'groups_id': [(5, 0), (4, self.env.ref('base.group_user').id), (4, self.env.ref('website.group_website_publisher').id)]
        })
        self.env.ref('website_slides.slide_channel_demo_0_gard_0')._remove_membership(self.env.ref('base.partner_demo').ids)

        self.phantom_js(
            '/slides',
            'odoo.__DEBUG__.services["web_tour.tour"].run("course_member")',
            'odoo.__DEBUG__.services["web_tour.tour"].tours.course_member.ready',
            login=user_demo.login)

    def test_course_member_portal(self):
        # remove membership because we need to be able to join the course during the tour
        # group_website_designer
        user_portal = self.env.ref('base.demo_user0')
        user_portal.flush()
        self.env.ref('website_slides.slide_channel_demo_0_gard_0')._remove_membership(self.env.ref('base.partner_demo_portal').ids)

        self.phantom_js(
            '/slides',
            'odoo.__DEBUG__.services["web_tour.tour"].run("course_member")',
            'odoo.__DEBUG__.services["web_tour.tour"].tours.course_member.ready',
            login=user_portal.login)


@tests.common.tagged('external', '-standard')
class TestUiYoutube(tests.HttpCase):

    def test_course_member_yt_employee(self):
        # remove membership because we need to be able to join the course during the tour
        user_demo = self.env.ref('base.user_demo')
        user_demo.flush()
        user_demo.write({
            'groups_id': [(5, 0), (4, self.env.ref('base.group_user').id)]
        })
        self.env.ref('website_slides.slide_channel_demo_3_furn0')._remove_membership(self.env.ref('base.partner_demo').ids)

        self.phantom_js(
            '/slides',
            'odoo.__DEBUG__.services["web_tour.tour"].run("course_member_youtube")',
            'odoo.__DEBUG__.services["web_tour.tour"].tours.course_member_youtube.ready',
            login=user_demo.login)

    def test_course_publisher_website_designer(self):
        # remove membership because we need to be able to join the course during the tour
        # group_website_designer
        user_demo = self.env.ref('base.user_demo')
        user_demo.flush()
        user_demo.write({
            'groups_id': [(5, 0), (4, self.env.ref('base.group_user').id), (4, self.env.ref('website.group_website_designer').id)]
        })

        self.phantom_js(
            '/slides',
            'odoo.__DEBUG__.services["web_tour.tour"].run("course_publisher")',
            'odoo.__DEBUG__.services["web_tour.tour"].tours.course_publisher.ready',
            login=user_demo.login)
