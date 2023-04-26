# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged
from odoo.addons.base.models.res_users import Users

from unittest.mock import patch


@tagged('-at_install', 'post_install')
class TestUserModifyOwnProfile(HttpCase):

    def test_user_modify_own_profile(self):
        """" A user should be able to modify their own profile.
        Even if that user does not have access rights to write on the res.users model. """

        # avoid 'reload_context' action in the middle of the tour to ease steps and form save checks
        with patch.object(Users, 'preference_save', lambda self: True):
            self.start_tour("/web", "mail/static/tests/tours/user_modify_own_profile_tour.js", login="demo", step_delay=100)
        self.assertEqual(self.env.ref('base.user_demo').email, "updatedemail@example.com")
