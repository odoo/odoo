from pathlib import Path
from types import SimpleNamespace

from odoo.tools.assets.esbuild import EsbuildCompiler

ROOT = Path("/odoo")


def _compiler(mirror_roots):
    compiler = EsbuildCompiler("web.assets_tests", [])
    compiler._mirror_roots = mirror_roots
    return compiler


def _asset(url):
    return SimpleNamespace(url=url, _filename=None)


class TestMirroredEntryPaths:
    LAYOUT = Path("/tmp/layout/website/static/src")

    def test_a_source_module_of_a_mirrored_addon_is_its_mirror_copy(self):
        compiler = _compiler({"website": self.LAYOUT})
        path = compiler._entry_path(_asset("/website/static/src/core/x.js"), ROOT)
        assert path == "/tmp/layout/website/static/src/core/x.js"

    def test_a_test_module_of_a_mirrored_addon_is_spelled_through_the_layout(self):
        # `@website/../tests/tours/x` resolves through the layout's symlinked
        # `tests` sibling and esbuild preserves symlinks there; the entry must
        # spell the same path or the tour registers twice
        compiler = _compiler({"website": self.LAYOUT})
        url = "/website/static/tests/tours/snippets_all_drag_and_drop.js"
        assert (
            compiler._entry_path(_asset(url), ROOT)
            == "/tmp/layout/website/static/tests/tours/snippets_all_drag_and_drop.js"
        )

    def test_an_addon_that_is_not_mirrored_keeps_its_real_path(self):
        compiler = _compiler({"website": self.LAYOUT})
        url = "/website_event/static/tests/tours/sub_templates_config.js"
        assert (
            compiler._entry_path(_asset(url), ROOT)
            == "./addons/website_event/static/tests/tours/sub_templates_config.js"
        )

    def test_a_reached_module_of_a_mirrored_addon_is_spelled_through_the_layout(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            "odoo.tools.misc.file_path", lambda rel: str(ROOT / "addons" / rel)
        )
        compiler = _compiler({"website": self.LAYOUT})
        assert (
            compiler._reached_module_path("/website/static/src/core/y.js", ROOT)
            == "/tmp/layout/website/static/src/core/y.js"
        )
        assert (
            compiler._reached_module_path("/portal/static/src/z.js", ROOT)
            == "./addons/portal/static/src/z.js"
        )
