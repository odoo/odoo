# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tests


@tests.common.tagged('post_install', '-at_install')
class TestUi(tests.HttpCase):

    def test_course_certification_employee(self):
        # remove membership because we need to be able to join the course during the tour
        user_demo = self.env.ref('base.user_demo')
        user_demo.flush()
        user_demo.write({
            'groups_id': [(5, 0), (4, self.env.ref('base.group_user').id)]
        })
        self.env.ref('website_slides.slide_channel_demo_6_furn3')._remove_membership(self.env.ref('base.partner_demo').ids)

        self.phantom_js(
            '/slides',
            'odoo.__DEBUG__.services["web_tour.tour"].run("certification_member")',
            'odoo.__DEBUG__.services["web_tour.tour"].tours.certification_member.ready',
            login=user_demo.login)
