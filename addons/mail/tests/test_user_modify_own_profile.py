# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@tagged('-at_install', 'post_install')
class TestUserModifyOwnProfile(HttpCaseWithUserDemo):

    def test_user_modify_own_profile(self):
        """" A user should be able to modify their own profile.
        Even if that user does not have access rights to write on the res.users model. """
        if 'hr.employee' in self.env and not self.user_demo.employee_id:
            self.env['hr.employee'].create({
                'name': 'Marc Demo',
                'user_id': self.user_demo.id,
            })
        self.user_demo.tz = "Europe/Brussels"
        self.start_tour("/web", "mail/static/tests/tours/user_modify_own_profile_tour.js", login="demo")
<<<<<<< HEAD
        self.assertEqual(self.partner_demo.email, "updatedemail@example.com")
||||||| parent of 7c08ab9d16ad (temp)
        self.assertEqual(self.env.ref('base.user_demo').email, "updatedemail@example.com")
=======
        self.assertEqual(self.user_demo.email, "updatedemail@example.com")
>>>>>>> 7c08ab9d16ad (temp)
