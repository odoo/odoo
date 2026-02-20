# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestSnippetBackgroundVideo(odoo.tests.HttpCase):

    def test_snippet_background_video(self):
        self.start_tour(self.env["website"].get_client_action_url("/", True), "snippet_background_video", login="admin")
