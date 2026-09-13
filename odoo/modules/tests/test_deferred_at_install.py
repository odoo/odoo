import unittest
from unittest.mock import patch

from odoo.modules.loading import get_installed_not_yet_loaded
from odoo.modules.module import _DEFAULT_MANIFEST, Manifest
from odoo.modules.module_graph import ModuleGraph
from odoo.tools import mute_logger


class _NoCursor:
    rowcount = 0

    def execute(self, query, *args, **kwargs):
        raise AssertionError("this test's graph must not reach the database")

    def fetchall(self):
        raise AssertionError("this test's graph must not reach the database")


DEPENDENCY = {
    "base": [],
    "hr": ["base"],
    "hr_work_entry": ["hr"],
    "hr_payroll": ["hr_work_entry"],
    "mail": ["base"],
}


def _make_manifest(name, **kw):
    if name not in DEPENDENCY:
        return None
    return Manifest(
        path="/dummy/" + name,
        manifest_content=dict(
            _DEFAULT_MANIFEST,
            author="test",
            license="LGPL-3",
            depends=DEPENDENCY[name],
        ),
    )


class TestDeferredAtInstall(unittest.TestCase):
    """An at_install suite waits for every installed module whose columns the
    tables already carry and whose models the registry does not hold yet."""

    @mute_logger("odoo.modules.module_graph")
    def _graph(self, states):
        with (
            patch("odoo.modules.module_graph.ModuleGraph._update_from_database"),
            patch("odoo.modules.module_graph.Manifest.for_addon", _make_manifest),
            patch(
                "odoo.modules.module_graph.ModuleGraph._imported_modules",
                {"studio_customization"},
            ),
        ):
            graph = ModuleGraph(_NoCursor())
            graph.extend(list(DEPENDENCY))
        for node in graph:
            node.state = states.get(node.name, "installed")
        return graph

    def test_an_installed_module_still_to_load_defers(self):
        graph = self._graph({})
        self.assertEqual(
            get_installed_not_yet_loaded(graph, "hr", {"base", "hr"}),
            ["mail", "hr_work_entry", "hr_payroll"],
        )

    def test_the_pending_list_follows_load_order(self):
        graph = self._graph({})
        with patch.object(ModuleGraph, "installed_outside", return_value=[]):
            self.assertEqual(
                get_installed_not_yet_loaded(graph, "base", {"base"}),
                ["hr", "mail", "hr_work_entry", "hr_payroll"],
            )

    def test_base_defers_to_installed_modules_the_bootstrap_graph_does_not_hold(self):
        graph = self._graph({})
        with patch.object(
            ModuleGraph, "installed_outside", return_value=["crm", "base", "hr"]
        ):
            self.assertEqual(
                get_installed_not_yet_loaded(graph, "base", {"base"}),
                ["hr", "mail", "hr_work_entry", "hr_payroll", "crm"],
            )

    def test_only_base_consults_the_database(self):
        graph = self._graph({})
        with patch.object(
            ModuleGraph, "installed_outside", return_value=["crm"]
        ) as outside:
            get_installed_not_yet_loaded(graph, "hr", {"base", "hr"})
        outside.assert_not_called()

    def test_a_loaded_module_no_longer_counts(self):
        graph = self._graph({})
        loaded = {"base", "hr", "mail", "hr_work_entry", "hr_payroll"}
        self.assertEqual(get_installed_not_yet_loaded(graph, "hr", loaded), [])

    def test_a_module_being_installed_has_no_columns_yet(self):
        # A fresh `-i hr,hr_work_entry,mail`: hr's tests run at install, as before.
        graph = self._graph(
            {
                "hr_work_entry": "to install",
                "hr_payroll": "to install",
                "mail": "to install",
            }
        )
        self.assertEqual(get_installed_not_yet_loaded(graph, "hr", {"base", "hr"}), [])

    def test_a_module_about_to_upgrade_already_has_its_columns(self):
        # `-u hr` on a database holding hr_work_entry marks both to upgrade.
        graph = self._graph(
            {"hr": "to upgrade", "hr_work_entry": "to upgrade", "mail": "to install"}
        )
        self.assertEqual(
            get_installed_not_yet_loaded(graph, "hr", {"base", "hr"}),
            ["hr_work_entry", "hr_payroll"],
        )

    def test_an_unrelated_installed_module_counts_too(self):
        # mail puts a NOT NULL column on res_users without depending on the module
        # whose tests create a user; the schema is the criterion, not the graph edge.
        graph = self._graph({})
        self.assertEqual(
            get_installed_not_yet_loaded(graph, "mail", {"base", "mail"}),
            ["hr", "hr_work_entry", "hr_payroll"],
        )
