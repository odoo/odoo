# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import Form, HttpCase, tagged

from odoo.addons.base.models.assetsbundle import AssetsBundle
from odoo.addons.website_livechat import _post_init_hook

from .common import TestLivechatCommon


@tagged("-at_install", "post_install")
class TestWebsiteLivechatThemeColors(TestLivechatCommon):
    def _set_palette_colors(self, website, colors):
        self.env["website.assets"].with_context(website_id=website.id).make_scss_customization(
            "/website/static/src/scss/options/colors/user_color_palette.scss",
            colors,
        )

    def test_follows_the_theme_of_its_website(self):
        website = self.env.ref("base.default_website")
        self._set_palette_colors(website, {"o-color-1": "#112233", "o-color-2": "#445566"})
        self.assertTrue(self.livechat_channel.follow_website_theme)
        self.assertEqual(self.livechat_channel._get_livechat_colors(), {
            "primary_color": "#112233", "secondary_color": "#445566",
        })
        # A theme change applies at once, nothing is stored on the channel.
        self._set_palette_colors(website, {"o-color-1": "#eeeeee"})
        self.assertEqual(self.livechat_channel._get_livechat_colors()["primary_color"], "#eeeeee")
        self.assertNotEqual(self.livechat_channel.primary_color, "#eeeeee")

    def test_chat_options_use_the_theme_colors(self):
        website = self.env.ref("base.default_website")
        self._set_palette_colors(website, {"o-color-1": "#112233", "o-color-2": "#445566"})
        infos = self.livechat_channel._get_channel_infos()
        self.assertEqual(infos["primary_color"], "#112233")
        self.assertEqual(infos["secondary_color"], "#445566")

    def test_custom_colors_when_not_following(self):
        website = self.env.ref("base.default_website")
        self._set_palette_colors(website, {"o-color-1": "#112233"})
        self.livechat_channel.write({
            "follow_website_theme": False, "primary_color": "#000000", "secondary_color": "#ffffff",
        })
        self.assertEqual(self.livechat_channel._get_livechat_colors(), {
            "primary_color": "#000000", "secondary_color": "#ffffff",
        })

    def test_channel_without_website_uses_its_own_colors(self):
        channel = self.env["im_livechat.channel"].create({"name": "No website", "primary_color": "#000000"})
        self.assertTrue(channel.follow_website_theme)
        self.assertFalse(channel.has_website)
        self.assertEqual(channel._get_livechat_colors()["primary_color"], "#000000")

    def test_shared_channel_follows_the_current_website(self):
        website_a = self.env.ref("base.default_website")
        self._set_palette_colors(website_a, {"o-color-1": "#112233"})
        website_b = self.env["website"].create({"name": "Second website", "sequence": website_a.sequence + 1})
        website_b.channel_id = self.livechat_channel
        self._set_palette_colors(website_b, {"o-color-1": "#eeeeee"})
        channel = self.livechat_channel
        self.assertEqual(channel.with_context(website_id=website_a.id)._get_livechat_colors()["primary_color"], "#112233")
        self.assertEqual(channel.with_context(website_id=website_b.id)._get_livechat_colors()["primary_color"], "#eeeeee")

    def test_theme_colors_normalized_to_lowercase_hex(self):
        website = self.env.ref("base.default_website")
        self._set_palette_colors(website, {"o-color-1": "#ABCDEF", "o-color-2": "#FFF"})
        self.assertEqual(self.livechat_channel._get_livechat_colors(), {
            "primary_color": "#abcdef", "secondary_color": "#ffffff",
        })

    def test_theme_colors_skip_translucent_values(self):
        website = self.env.ref("base.default_website")
        self.livechat_channel.primary_color = "#123456"
        self._set_palette_colors(website, {"o-color-1": "rgba(10, 20, 30, 0.5)"})
        self.assertNotIn("primary_color", self.livechat_channel._get_website_theme_colors(website))

    def test_theme_colors_read_colors_libsass_prints_by_name(self):
        website = self.env.ref("base.default_website")
        self._set_palette_colors(website, {"o-color-1": "rgb(255, 0, 0)", "o-color-2": "white"})
        self.assertEqual(self.livechat_channel._get_livechat_colors(), {
            "primary_color": "#ff0000", "secondary_color": "#ffffff",
        })

    def test_failing_export_falls_back_to_the_channel_colors(self):
        self.livechat_channel.primary_color = "#123456"
        with patch.object(self.registry["website"], "_get_scss_exports", side_effect=ValueError("boom")), \
                self.assertLogs("odoo.addons.website_livechat.models.im_livechat_channel", "WARNING"):
            colors = self.livechat_channel._get_livechat_colors()
        self.assertEqual(colors["primary_color"], "#123456")

    def test_reading_theme_colors_does_not_compile_frontend_bundle(self):
        website = self.env.ref("base.default_website")
        self._set_palette_colors(website, {"o-color-1": "#112233"})
        with patch.object(AssetsBundle, "css") as css:
            self.assertEqual(self.livechat_channel._get_livechat_colors()["primary_color"], "#112233")
        css.assert_not_called()

    def test_install_follows_only_default_website_channels(self):
        website = self.env.ref("base.default_website")
        default_channel, custom_channel, unlinked_channel = self.env["im_livechat.channel"].create([
            {"name": "Default colors"},
            {"name": "Custom colors", "primary_color": "#000000"},
            {"name": "No website"},
        ])
        website.channel_id = default_channel
        self.env["website"].create({"name": "Second website", "channel_id": custom_channel.id})
        _post_init_hook(self.env)
        self.assertTrue(default_channel.follow_website_theme)
        self.assertFalse(custom_channel.follow_website_theme)
        self.assertFalse(unlinked_channel.follow_website_theme)

    def test_stop_following_starts_from_the_theme_colors(self):
        website = self.env.ref("base.default_website")
        self._set_palette_colors(website, {"o-color-1": "#112233", "o-color-2": "#445566"})
        with Form(self.livechat_channel) as channel_form:
            self.assertEqual(channel_form.website_primary_color, "#112233")
            channel_form.follow_website_theme = False
            self.assertEqual(channel_form.primary_color, "#112233")
            self.assertEqual(channel_form.secondary_color, "#445566")
        self.assertEqual(self.livechat_channel._get_livechat_colors()["primary_color"], "#112233")


@tagged("-at_install", "post_install")
class TestWebsiteLivechatThemeColorsTour(HttpCase, TestLivechatCommon):
    def test_chat_follows_the_theme_colors(self):
        website = self.env.ref("base.default_website")
        self.env["website.assets"].with_context(website_id=website.id).make_scss_customization(
            "/website/static/src/scss/options/colors/user_color_palette.scss",
            {"o-color-1": "#112233", "o-color-2": "#445566"},
        )
        self.start_tour("/", "website_livechat_theme_colors", login=None)
