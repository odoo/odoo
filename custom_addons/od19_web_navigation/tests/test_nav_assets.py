from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged("post_install", "-at_install")
class TestNavigationAssets(HttpCase):
    """The Back/Forward navigation assets must be wired into the backend bundle."""

    def _backend_asset_urls(self):
        assets = self.env["ir.qweb"]._get_asset_content("web.assets_backend")[0]
        return [asset["url"] for asset in assets]

    def test_nav_assets_in_backend_bundle(self):
        urls = self._backend_asset_urls()
        self.assertIn(
            "/od19_web_navigation/static/src/js/od19_nav_history.js",
            urls,
        )
        self.assertIn(
            "/od19_web_navigation/static/src/js/od19_nav_buttons.js",
            urls,
        )
        self.assertIn(
            "/od19_web_navigation/static/src/css/od19_nav_buttons.css",
            urls,
        )
