# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
import odoo.tests


@odoo.tests.tagged('-at_install', 'post_install')
class TestWebsiteFieldSanitize(odoo.tests.HttpCase):
    def test_sanitize_video_iframe(self):
        self.env['res.users'].create({
            'name': 'Restricted Editor',
            'login': 'restricted',
            'password': 'restricted',
            'group_ids': [(6, 0, [
                self.ref('base.group_user'),
                self.ref('website.group_website_restricted_editor'),
                self.ref('test_website.group_test_website_admin'),
            ])]
        })

        # Add a video to an HTML field (admin).
        self.start_tour(
            self.env['website'].get_client_action_url('/test_website/model_item/1'),
            'website_designer_iframe_video',
            login='admin'
        )
        # Make sure a user can still edit the content (restricted editor).
        self.start_tour(
            self.env['website'].get_client_action_url('/test_website/model_item/1'),
            'website_restricted_editor_iframe_video',
            login='restricted'
        )
