from unittest.mock import MagicMock, patch

import pytest

from odoo.modules import migration


@pytest.fixture
def manager():
    def _make(sources, *, installed="1.0", target="2.0", state="to upgrade"):
        mgr = object.__new__(migration.MigrationManager)
        mgr.cr = MagicMock()
        mgr.graph = []
        mgr.migrations = {"mymod": sources}
        pkg = MagicMock()
        pkg.name = "mymod"
        pkg.load_state = state
        pkg.load_version = installed
        pkg.manifest = {"version": target}
        return mgr, pkg

    return _make


def _run(mgr, pkg, stage):
    executed = []

    def fake_run(cr, installed_version, pyfile, addon, stg, version=None):
        executed.append((version, pyfile))

    with patch.object(migration, "run_migration_script", side_effect=fake_run):
        mgr.migrate_module(pkg, stage)
    return executed


class TestStageSelection:
    def test_only_scripts_for_the_requested_stage_run(self, manager):
        mgr, pkg = manager(
            {"module": {"1.5": ["m/1.5/pre-a.py", "m/1.5/post-b.py", "m/1.5/end-c.py"]}}
        )
        assert [f for _, f in _run(mgr, pkg, "pre")] == ["m/1.5/pre-a.py"]
        assert [f for _, f in _run(mgr, pkg, "post")] == ["m/1.5/post-b.py"]
        assert [f for _, f in _run(mgr, pkg, "end")] == ["m/1.5/end-c.py"]

    def test_a_module_not_being_upgraded_runs_nothing(self, manager):
        mgr, pkg = manager({"module": {"1.5": ["m/1.5/pre-a.py"]}}, state="installed")
        assert _run(mgr, pkg, "pre") == []

    def test_a_script_whose_name_only_contains_the_stage_is_not_matched(self, manager):
        mgr, pkg = manager({"module": {"1.5": ["m/1.5/fixup-pre-a.py"]}})
        assert _run(mgr, pkg, "pre") == [], (
            "the prefix is the marker; matching anywhere in the name would run "
            "a `post-` script during `pre`"
        )

    def test_an_unknown_stage_is_refused(self, manager):
        mgr, pkg = manager({"module": {}})
        with pytest.raises(ValueError, match="invalid migration stage 'middle'"):
            mgr.migrate_module(pkg, "middle")


class TestVersionOrdering:
    def test_versions_run_oldest_first(self, manager):
        mgr, pkg = manager(
            {
                "module": {
                    "1.10": ["m/1.10/pre-a.py"],
                    "1.2": ["m/1.2/pre-a.py"],
                    "1.9": ["m/1.9/pre-a.py"],
                }
            }
        )
        assert [v for v, _ in _run(mgr, pkg, "pre")] == [
            "[>1.2]",
            "[>1.9]",
            "[>1.10]",
        ], (
            "sorted as versions, not as strings — lexically '1.10' precedes "
            "'1.2', which would replay an older fix-up over a newer one"
        )

    def test_a_version_outside_the_upgrade_window_is_skipped(self, manager):
        mgr, pkg = manager(
            {
                "module": {
                    "19.0.0.9": ["m/0.9/pre-a.py"],
                    "19.0.1.5": ["m/1.5/pre-a.py"],
                }
            },
            installed="19.0.1.0",
            target="19.0.2.0",
        )
        assert [f for _, f in _run(mgr, pkg, "pre")] == ["m/1.5/pre-a.py"], (
            "19.0.0.9 is below the installed version; re-running it would undo "
            "work the module has already done"
        )

    def test_a_version_above_the_target_is_not_run_early(self, manager):
        mgr, pkg = manager(
            {"module": {"19.0.3.0": ["m/3.0/pre-a.py"]}},
            installed="19.0.1.0",
            target="19.0.2.0",
        )
        assert _run(mgr, pkg, "pre") == []


class TestTheAlwaysRunMarker:
    def test_it_runs_first_in_the_pre_stage(self, manager):
        mgr, pkg = manager(
            {"module": {"0.0.0": ["m/0.0.0/pre-a.py"], "1.5": ["m/1.5/pre-b.py"]}}
        )
        assert [f for _, f in _run(mgr, pkg, "pre")] == [
            "m/0.0.0/pre-a.py",
            "m/1.5/pre-b.py",
        ], (
            "a pre-migration that always runs prepares the schema the versioned "
            "ones then rely on; running it after them is the wrong way round"
        )

    @pytest.mark.parametrize("stage", ["post", "end"])
    def test_it_runs_last_in_the_other_stages(self, manager, stage):
        mgr, pkg = manager(
            {
                "module": {
                    "0.0.0": [f"m/0.0.0/{stage}-a.py"],
                    "1.5": [f"m/1.5/{stage}-b.py"],
                }
            }
        )
        assert [f for _, f in _run(mgr, pkg, stage)] == [
            f"m/1.5/{stage}-b.py",
            f"m/0.0.0/{stage}-a.py",
        ], "an always-run clean-up goes after the versioned work, not before it"

    def test_it_is_labelled_with_the_stage_marker(self, manager):
        mgr, pkg = manager({"module": {"0.0.0": ["m/0.0.0/pre-a.py"]}})
        assert [v for v, _ in _run(mgr, pkg, "pre")] == ["[>0.0.0]"]
        mgr, pkg = manager({"module": {"0.0.0": ["m/0.0.0/end-a.py"]}})
        assert [v for v, _ in _run(mgr, pkg, "end")] == ["[$0.0.0]"]


class TestAcrossTheThreeSources:
    def test_scripts_from_every_source_run_for_the_same_version(self, manager):
        mgr, pkg = manager(
            {
                "module": {"1.5": ["mod/1.5/pre-b.py"]},
                "module_upgrades": {"1.5": ["upg/1.5/pre-a.py"]},
                "upgrade": {"1.5": ["path/1.5/pre-c.py"]},
            }
        )
        assert [f for _, f in _run(mgr, pkg, "pre")] == [
            "upg/1.5/pre-a.py",
            "mod/1.5/pre-b.py",
            "path/1.5/pre-c.py",
        ], (
            "ordered by BASENAME across sources, so an author numbering "
            "pre-10/pre-20 gets that order regardless of which tree each lives "
            "in"
        )

    def test_a_version_present_in_only_one_source_still_runs(self, manager):
        mgr, pkg = manager(
            {
                "module": {},
                "module_upgrades": {"1.5": ["upg/1.5/pre-a.py"]},
                "upgrade": {},
            }
        )
        assert [f for _, f in _run(mgr, pkg, "pre")] == ["upg/1.5/pre-a.py"]

    def test_a_version_with_no_files_contributes_no_scripts(self, manager):
        mgr, pkg = manager({"module": {"1.5": [], "1.6": ["m/1.6/pre-a.py"]}})
        assert [v for v, _ in _run(mgr, pkg, "pre")] == ["[>1.6]"]

    def test_identical_basenames_fall_back_to_the_full_path(self, manager):
        mgr, pkg = manager(
            {
                "module": {"1.5": ["z/1.5/pre-a.py"]},
                "module_upgrades": {"1.5": ["a/1.5/pre-a.py"]},
            }
        )
        assert [f for _, f in _run(mgr, pkg, "pre")] == [
            "a/1.5/pre-a.py",
            "z/1.5/pre-a.py",
        ], "a tie on basename must still order deterministically"
