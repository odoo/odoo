# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, HttpCase


@tagged('-at_install', 'post_install')
class TestForm(HttpCase):

    def test_form_conditional_visibility_record_field(self):
        self.start_tour(
            self.env['website'].get_client_action_url('/test_website/model_item/1'),
            'test_form_conditional_visibility_record_field',
            login='admin',
        )
