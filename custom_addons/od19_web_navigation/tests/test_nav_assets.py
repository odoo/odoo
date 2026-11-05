from pathlib import Path

from odoo.modules.module import get_module_path
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged("post_install", "-at_install")
class TestNavigationAssets(HttpCase):
    """The Back/Forward navigation assets must be wired into the backend bundle."""

    def _backend_asset_urls(self):
        assets = self.env["ir.qweb"]._get_asset_content("web.assets_backend")[0]
        return [asset["url"] for asset in assets]

    def _module_file_text(self, relative_path):
        module_path = Path(get_module_path("od19_web_navigation"))
        return (module_path / relative_path).read_text(encoding="utf-8")

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
            "/od19_web_navigation/static/src/xml/od19_nav_buttons.xml",
            urls,
        )
        self.assertIn(
            "/od19_web_navigation/static/src/css/od19_nav_buttons.css",
            urls,
        )

    def test_nav_buttons_use_segmented_navbar_structure(self):
        component_source = self._module_file_text("static/src/js/od19_nav_buttons.js")
        stylesheet_source = self._module_file_text("static/src/css/od19_nav_buttons.css")
        self.assertIn("od19-nav-segmented", component_source)
        self.assertIn("od19-nav-segmented__divider", component_source)
        self.assertIn(".od19-nav-segmented", stylesheet_source)
        self.assertIn(".od19-nav-segmented__btn", stylesheet_source)

    def test_history_reads_canonical_state_from_session_storage(self):
        """The router state must be read from sessionStorage, not from the
        debounced `router.current`, otherwise the recorded history is stale and
        Back/Forward cannot replay anything."""
        history_source = self._module_file_text("static/src/js/od19_nav_history.js")
        self.assertIn('sessionStorage.getItem("current_state")', history_source)
