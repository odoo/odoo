from types import SimpleNamespace
from unittest.mock import patch

from odoo.tools.assets import esm_registry


def _manifest(name, esm):
    return SimpleNamespace(name=name, path=f"/x/{name}", esm=esm, manifest={"esm": esm})


def _build(*manifests):
    with (
        patch.object(
            esm_registry,
            "_validated_esm_section",
            lambda manifest: manifest.esm,
        ),
        patch("odoo.modules.Manifest.get_all_addon_manifests", lambda: list(manifests)),
    ):
        return esm_registry._prepare_esm_registry()


class TestBundleOwners:
    def test_a_bundle_named_after_another_module_is_owned_by_its_declarer(self):
        registry = _build(
            _manifest(
                "pos_enterprise",
                {
                    "bundles": [
                        "pos_preparation_display.assets",
                        "pos_preparation_display.assets_tour_tests",
                    ],
                    "secondary_import_map_includes": {
                        "pos_preparation_display.assets": [
                            "pos_preparation_display.assets_tour_tests"
                        ]
                    },
                },
            ),
            _manifest("web", {"bundles": ["web.assets_web"]}),
        )
        assert (
            registry.bundle_addon("pos_preparation_display.assets") == "pos_enterprise"
        )
        assert (
            registry.bundle_addon("pos_preparation_display.assets_tour_tests")
            == "pos_enterprise"
        )
        assert registry.bundle_addon("web.assets_web") == "web"

    def test_a_bundle_nobody_declared_answers_its_prefix(self):
        registry = _build(_manifest("web", {"bundles": ["web.assets_web"]}))
        assert registry.bundle_addon("website.assets_wysiwyg") == "website"
        assert "web.assets_web" not in registry.bundle_owners
