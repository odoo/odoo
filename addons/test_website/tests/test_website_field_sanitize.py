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
            'groups_id': [(6, 0, [
                self.ref('base.group_user'),
                self.ref('website.group_website_restricted_editor')
            ])]
        })
        self.record = self.env['test.model'].create({
            'name': 'Test Record',
            'website_description': """
                <div class="o_test_website_description">
                    A simple sanitize friendly content.
                    <i class="fa fa-heart"/>
                </div>
            """,
        })

        # Add a video to an HTML field (admin).
        self.start_tour(
            self.env['website'].get_client_action_url(f'/test_website/model_item/{self.record.id}', True),
            'website_designer_iframe_video',
            login='admin'
        )
        # Make sure a user can still edit the content (restricted editor).
        self.start_tour(
            self.env['website'].get_client_action_url(f'/test_website/model_item/{self.record.id}', True),
            'website_restricted_editor_iframe_video',
            login='restricted'
        )
