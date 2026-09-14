from types import SimpleNamespace
from unittest.mock import patch

import pytest

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


class TestDynamicChildrenFrom:
    def _pages(self, *extra):
        return (
            _manifest(
                "web",
                {
                    "bundles": ["web.assets_web", "web.assets_emoji"],
                    "dynamic_children": {"web.assets_web": ["web.assets_emoji"]},
                },
            ),
            _manifest(
                "spreadsheet",
                {
                    "bundles": ["spreadsheet.o_spreadsheet"],
                    "dynamic_children": {
                        "web.assets_web": ["spreadsheet.o_spreadsheet"]
                    },
                },
            ),
            *extra,
        )

    def test_a_second_backend_page_takes_every_child_of_the_base_page(self):
        registry = _build(
            *self._pages(
                _manifest(
                    "knowledge",
                    {
                        "bundles": ["knowledge.webclient"],
                        "dynamic_children_from": {
                            "knowledge.webclient": "web.assets_web"
                        },
                    },
                )
            )
        )
        assert registry.dynamic_children["knowledge.webclient"] == (
            "web.assets_emoji",
            "spreadsheet.o_spreadsheet",
        )
        assert registry.dynamic_children["web.assets_web"] == (
            "web.assets_emoji",
            "spreadsheet.o_spreadsheet",
        )

    def test_a_page_keeps_children_of_its_own_beside_the_inherited_ones(self):
        registry = _build(
            *self._pages(
                _manifest(
                    "knowledge",
                    {
                        "bundles": ["knowledge.webclient", "knowledge.extra"],
                        "dynamic_children": {
                            "knowledge.webclient": ["knowledge.extra"]
                        },
                        "dynamic_children_from": {
                            "knowledge.webclient": "web.assets_web"
                        },
                    },
                )
            )
        )
        assert registry.dynamic_children["knowledge.webclient"] == (
            "knowledge.extra",
            "web.assets_emoji",
            "spreadsheet.o_spreadsheet",
        )
        assert "knowledge.extra" in registry.runtime_bundle_names

    def test_restating_an_inherited_child_is_refused(self):
        with pytest.raises(ValueError, match="restates"):
            _build(
                *self._pages(
                    _manifest(
                        "knowledge",
                        {
                            "bundles": ["knowledge.webclient"],
                            "dynamic_children": {
                                "knowledge.webclient": ["web.assets_emoji"]
                            },
                            "dynamic_children_from": {
                                "knowledge.webclient": "web.assets_web"
                            },
                        },
                    )
                )
            )

    def test_an_unregistered_base_is_refused(self):
        with pytest.raises(ValueError, match="not a registered ESM bundle"):
            _build(
                *self._pages(
                    _manifest(
                        "knowledge",
                        {
                            "bundles": ["knowledge.webclient"],
                            "dynamic_children_from": {
                                "knowledge.webclient": "web.assets_backend"
                            },
                        },
                    )
                )
            )

    def test_a_chain_of_bases_is_refused(self):
        with pytest.raises(ValueError, match="takes its own dynamic children"):
            _build(
                *self._pages(
                    _manifest(
                        "knowledge",
                        {
                            "bundles": ["knowledge.webclient", "knowledge.print"],
                            "dynamic_children_from": {
                                "knowledge.webclient": "web.assets_web",
                                "knowledge.print": "knowledge.webclient",
                            },
                        },
                    )
                )
            )

    def test_two_bases_for_one_page_are_refused(self):
        with pytest.raises(ValueError, match="names both"):
            _build(
                *self._pages(
                    _manifest(
                        "knowledge",
                        {
                            "bundles": ["knowledge.webclient"],
                            "dynamic_children_from": {
                                "knowledge.webclient": "web.assets_web"
                            },
                        },
                    ),
                    _manifest(
                        "document",
                        {
                            "dynamic_children_from": {
                                "knowledge.webclient": "spreadsheet.o_spreadsheet"
                            },
                        },
                    ),
                )
            )

    def test_a_base_that_is_not_a_single_name_is_refused(self):
        with pytest.raises(TypeError, match="one bundle name"):
            _build(
                *self._pages(
                    _manifest(
                        "knowledge",
                        {
                            "bundles": ["knowledge.webclient"],
                            "dynamic_children_from": {
                                "knowledge.webclient": ["web.assets_web"]
                            },
                        },
                    )
                )
            )
