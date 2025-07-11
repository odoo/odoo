# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo.tests import common, tagged
from odoo.addons.html_editor import tools


@tagged("post_install", "-at_install")
class TestVideoUtils(common.BaseCase):
    urls = {
        "facebook_video": "http://www.facebook.com/watch?v=2206239373151307",
        "facebook_reel": "https://www.facebook.com/reel/568986686120283",
    }

    def test_player_regexes(self):
        # facebook
        self.assertIsNotNone(re.search(tools.player_regexes["facebook"], TestVideoUtils.urls["facebook_video"]))
        self.assertIsNotNone(re.search(tools.player_regexes["facebook"], TestVideoUtils.urls["facebook_reel"]))

    def test_get_video_source_data(self):
        # facebook
        self.assertEqual("facebook", tools.get_video_source_data(TestVideoUtils.urls["facebook_video"])[0])
        self.assertEqual("2206239373151307", tools.get_video_source_data(TestVideoUtils.urls["facebook_video"])[1])
        self.assertEqual("facebook", tools.get_video_source_data(TestVideoUtils.urls["facebook_reel"])[0])
        self.assertEqual("568986686120283", tools.get_video_source_data(TestVideoUtils.urls["facebook_reel"])[1])
