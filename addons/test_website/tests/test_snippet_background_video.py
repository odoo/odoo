# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
import unittest

@odoo.tests.common.tagged('post_install', '-at_install')
class TestSnippetBackgroundVideo(odoo.tests.HttpCase):
    # TODO master-mysterious-egg fix error
    @unittest.skip("prepare mysterious-egg for merging")
    def test_snippet_background_video(self):
        self.start_tour("/", "snippet_background_video", login="admin")
