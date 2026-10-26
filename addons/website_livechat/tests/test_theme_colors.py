# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from unittest.mock import patch

from odoo.tests import tagged

from .common import TestLivechatCommon


@tagged("-at_install", "post_install")
class TestWebsiteLivechatThemeColors(TestLivechatCommon):
    def setUp(self):
        super().setUp()
        # Run the sync scheduled by linking the channel in the common setup.
        self.env.cr.precommit.run()

    def _set_palette_colors(self, website, colors):
        # In practice, each customization is its own request. The asset bundle
        # version follows the customized file's write date, so move the clock
        # forward to get a new version, and run what would run on commit.
        self.palette_change_count = getattr(self, "palette_change_count", 0) + 1
        now = self.env.cr.now() + timedelta(seconds=self.palette_change_count)
        with patch.object(self.env.cr, "now", return_value=now):
            self.env["website.assets"].with_context(website_id=website.id).make_scss_customization(
                "/website/static/src/scss/options/colors/user_color_palette.scss",
                colors,
            )
        self.env.cr.precommit.run()

    def test_get_website_theme_colors_tracks_correct_website_palette(self):
        website_a = self.env.ref("base.default_website")
        self._set_palette_colors(website_a, {"o-color-1": "#112233"})
        website_b = self.env["website"].create({"name": "Second website"})
        channel_b = self.env["im_livechat.channel"].create({"name": "Second channel"})
        website_b.channel_id = channel_b.id
        self._set_palette_colors(website_b, {"o-color-1": "#eeeeee"})
        colors_a = self.livechat_channel.get_website_theme_colors()
        colors_b = channel_b.get_website_theme_colors()
        self.assertEqual(colors_a["primary_color"], "#112233")
        self.assertEqual(colors_b["primary_color"], "#eeeeee")

    def test_theme_colors_sync_when_website_palette_changes(self):
        website = self.env.ref("base.default_website")
        self._set_palette_colors(website, {"o-color-1": "#112233", "o-color-2": "#445566"})
        self.assertEqual(self.livechat_channel.primary_color, "#112233")
        self.assertEqual(self.livechat_channel.secondary_color, "#445566")
        self._set_palette_colors(website, {"o-color-1": "#eeeeee"})
        self.assertEqual(self.livechat_channel.primary_color, "#eeeeee")
        self.assertTrue(self.livechat_channel.theme_colors_synced)

    def test_theme_colors_do_not_sync_when_set_manually(self):
        website = self.env.ref("base.default_website")
        self._set_palette_colors(website, {"o-color-1": "#112233"})
        self.livechat_channel.primary_color = "#000000"
        self.assertFalse(self.livechat_channel.theme_colors_synced)
        self._set_palette_colors(website, {"o-color-1": "#eeeeee"})
        self.assertEqual(self.livechat_channel.primary_color, "#000000")

    def test_theme_colors_normalized_to_lowercase_hex(self):
        website = self.env.ref("base.default_website")
        self._set_palette_colors(website, {"o-color-1": "#ABCDEF", "o-color-2": "#FFF"})
        colors = self.livechat_channel.get_website_theme_colors()
        self.assertEqual(colors["primary_color"], "#abcdef")
        self.assertEqual(colors["secondary_color"], "#ffffff")
        self.livechat_channel.write({"primary_color": "#ABCDEF", "secondary_color": "#ffffff"})
        self.assertTrue(self.livechat_channel.theme_colors_synced)

    def test_theme_colors_skip_non_hex_values(self):
        website = self.env.ref("base.default_website")
        self._set_palette_colors(website, {"o-color-1": "rgba(10, 20, 30, 0.5)"})
        self.assertNotIn("primary_color", self.livechat_channel.get_website_theme_colors())

    def test_shared_channel_follows_first_website_only(self):
        website_a = self.env.ref("base.default_website")
        self._set_palette_colors(website_a, {"o-color-1": "#112233"})
        website_b = self.env["website"].create({"name": "Second website", "sequence": website_a.sequence + 1})
        website_b.channel_id = self.livechat_channel
        self.assertEqual(self.livechat_channel.primary_color, "#112233")
        self._set_palette_colors(website_b, {"o-color-1": "#eeeeee"})
        self.assertEqual(self.livechat_channel.primary_color, "#112233")
        self.assertTrue(self.livechat_channel.theme_colors_synced)

    def test_linking_channel_seeds_default_colors_only(self):
        website = self.env.ref("base.default_website")
        self._set_palette_colors(website, {"o-color-1": "#112233"})
        default_channel, custom_channel = self.env["im_livechat.channel"].create(
            [{"name": "Default colors"}, {"name": "Custom colors", "primary_color": "#000000"}]
        )
        website.channel_id = default_channel
        self.env.cr.precommit.run()
        self.assertEqual(default_channel.primary_color, "#112233")
        self.assertTrue(default_channel.theme_colors_synced)
        website.channel_id = custom_channel
        self.env.cr.precommit.run()
        self.assertEqual(custom_channel.primary_color, "#000000")
        self.assertFalse(custom_channel.theme_colors_synced)

    def test_theme_colors_sync_when_theme_is_loaded(self):
        website = self.env.ref("base.default_website")
        self.assertTrue(self.livechat_channel.theme_colors_synced)
        # A theme brings its own palette without going through the customization.
        with patch.object(self.registry["website"], "_schedule_livechat_theme_colors_sync"):
            self._set_palette_colors(website, {"o-color-1": "#112233"})
        self.assertNotEqual(self.livechat_channel.primary_color, "#112233")
        self.env["ir.module.module"]._theme_load(website)
        self.env.cr.precommit.run()
        self.assertEqual(self.livechat_channel.primary_color, "#112233")
        self.assertTrue(self.livechat_channel.theme_colors_synced)

    def test_unrelated_customization_does_not_sync(self):
        website = self.env.ref("base.default_website")
        with patch.object(self.registry["im_livechat.channel"], "_sync_theme_colors") as sync:
            self.env["website.assets"].with_context(website_id=website.id).make_scss_customization(
                "/website/static/src/scss/options/user_values.scss",
                {"btn-ripple": "true"},
            )
            self.env.cr.precommit.run()
        sync.assert_not_called()
