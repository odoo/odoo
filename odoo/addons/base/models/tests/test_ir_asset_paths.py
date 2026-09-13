import random
import re
from pathlib import Path

import pytest

from odoo.addons.base.models.ir_asset_paths import (
    AssetDirective,
    AssetDirectiveError,
    AssetPaths,
    BundleWalk,
    ResolvedPath,
    _get_static_files,
    _is_reachable_without_symlink,
    can_aggregate,
    fs_to_web,
    is_wildcard_glob,
)


def rp(path, full=None, mtime=1.0):
    return ResolvedPath(path, full if full is not None else "/full" + path, mtime)


def paths_of(asset_paths):
    return [entry.path for entry in asset_paths.list]


def make_walk(bundles, resolve=None, seed=(), seed_bundle="seed"):

    def prepare_directives(bundle):
        return [
            AssetDirective(directive, target, path, f"probe {directive} {path!r}")
            for directive, target, path in bundles.get(bundle, ())
        ]

    walk = BundleWalk(resolve or (lambda path_def: [rp(path_def)]), prepare_directives)
    if seed:
        walk.paths.append_paths([rp(p) for p in seed], seed_bundle)
    return walk


def resolver_for(mapping):
    return lambda path_def: [rp(p) for p in mapping.get(path_def, [path_def])]


class TestUrlClassification:
    @pytest.mark.parametrize(
        "url",
        [
            "web/static/src/a.js",
            "/web/static/src/a.js",
            "/web/static/src/**/*.scss",
        ],
    )
    def test_local_paths_can_be_aggregated(self, url):
        assert can_aggregate(url)

    @pytest.mark.parametrize(
        "url",
        [
            "http://cdn.example.com/a.js",
            "https://cdn.example.com/a.js",
            "//cdn.example.com/a.js",
            "/web/content/1234-abc/a.js",
        ],
    )
    def test_external_and_content_urls_cannot(self, url):
        assert not can_aggregate(url)

    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("/web/a.js", False),
            ("/web/*.js", True),
            ("/web/**/*.js", True),
            ("/web/file?.js", True),
            ("/web/file[14].js", True),
            ("/web/file].js", False),
        ],
    )
    def test_wildcard_detection(self, path, expected):
        assert is_wildcard_glob(path) is expected

    def test_fs2web_is_identity_on_posix(self):
        assert fs_to_web("a/b/c.js") == "a/b/c.js"


class TestAssetPathsBasics:
    def test_append_deduplicates_and_keeps_first_occurrence(self):
        ap = AssetPaths()
        ap.append_paths([rp("/a"), rp("/b")], "b1")
        ap.append_paths([rp("/b"), rp("/c")], "b2")
        assert paths_of(ap) == ["/a", "/b", "/c"]
        assert ap.list[1].bundle == "b1", "the first contributor keeps ownership"

    def test_memo_and_list_never_drift(self):
        ap = AssetPaths()
        ap.append_paths([rp("/a"), rp("/b"), rp("/c")], "b1")
        ap.remove_paths([rp("/b")], "b1")
        ap.insert_paths([rp("/d")], "b1", 0)
        assert ap.memo == set(paths_of(ap))

    def test_index_of_first_scans_in_target_order(self):
        ap = AssetPaths()
        ap.append_paths([rp("/a"), rp("/b")], "b1")
        assert ap.get_index_of_first(["/zzz", "/b", "/a"], "b1") == 1

    def test_index_of_first_names_the_bundle_when_nothing_matches(self):
        ap = AssetPaths()
        ap.append_paths([rp("/a")], "b1")
        with pytest.raises(ValueError, match="b1"):
            ap.get_index_of_first(["/x", "/y"], "b1")

    def test_remove_all_present_is_silent(self, caplog):
        ap = AssetPaths()
        ap.append_paths([rp("/a"), rp("/b")], "b1")
        ap.remove_paths([rp("/a")], "b1")
        assert paths_of(ap) == ["/b"]
        assert not caplog.records

    def test_remove_partially_present_warns_but_removes(self, caplog):
        ap = AssetPaths()
        ap.append_paths([rp("/a"), rp("/b")], "b1")
        ap.remove_paths([rp("/a"), rp("/gone")], "b1")
        assert paths_of(ap) == ["/b"]
        assert any("/gone" in record.getMessage() for record in caplog.records)

    def test_remove_nothing_present_raises_when_strict(self):
        ap = AssetPaths()
        ap.append_paths([rp("/a")], "b1")
        with pytest.raises(ValueError, match="b1"):
            ap.remove_paths([rp("/gone")], "b1")

    def test_remove_nothing_present_is_a_noop_when_not_strict(self, caplog):
        ap = AssetPaths()
        ap.append_paths([rp("/a")], "b1")
        ap.remove_paths([rp("/gone")], "b1", strict=False)
        assert paths_of(ap) == ["/a"]
        assert not caplog.records


class TestAnchors:
    def test_a_new_anchor_sits_at_the_end(self):
        ap = AssetPaths()
        ap.append_paths([rp("/a"), rp("/b")], "b1")
        assert ap.add_anchor().index == 2

    def test_inserting_at_an_anchor_leaves_it_on_the_new_head(self):
        ap = AssetPaths()
        ap.append_paths([rp("/a")], "b1")
        anchor = ap.add_anchor()
        ap.insert_paths([rp("/x")], "b2", anchor.index)
        ap.insert_paths([rp("/y")], "b2", anchor.index)
        assert paths_of(ap) == ["/a", "/y", "/x"], "later prepends go in front"

    def test_an_earlier_removal_drags_the_anchor_back(self):
        ap = AssetPaths()
        ap.append_paths([rp("/a"), rp("/b")], "parent")
        anchor = ap.add_anchor()
        assert anchor.index == 2
        ap.remove_paths([rp("/a")], "child")
        assert anchor.index == 1
        ap.insert_paths([rp("/x")], "child", anchor.index)
        assert paths_of(ap) == ["/b", "/x"], "prepend must not degrade to append"

    def test_release_stops_tracking_that_anchor_only(self):
        ap = AssetPaths()
        ap.append_paths([rp("/a")], "b1")
        first, second = ap.add_anchor(), ap.add_anchor()
        ap.remove_anchor(first)
        ap.insert_paths([rp("/x")], "b2", 0)
        assert first.index == 1, "a released anchor stops being maintained"
        assert second.index == 2, "a live one follows the shift"
        assert ap.anchors == [second]

    def test_released_anchors_are_matched_by_identity(self):
        ap = AssetPaths()
        first, second = ap.add_anchor(), ap.add_anchor()
        assert first.index == second.index == 0
        ap.remove_anchor(second)
        assert ap.anchors == [first]

    @pytest.mark.parametrize("seed", range(20))
    def test_an_open_anchor_always_splits_old_from_new(self, seed):
        rng = random.Random(seed)
        names = [f"/p{index}" for index in range(10)]
        ap = AssetPaths()
        frames = []
        for _step in range(24):
            before = set(paths_of(ap))
            operation = rng.choice(["open", "close", "append", "prepend", "remove"])
            if operation == "open":
                frames.append([ap.add_anchor(), paths_of(ap)])
            elif operation == "close" and frames:
                ap.remove_anchor(frames.pop()[0])
            elif operation == "append":
                ap.append_paths([rp(p) for p in rng.sample(names, 3)], "b")
            elif operation == "prepend" and frames:
                anchor = frames[-1][0]
                ap.insert_paths(
                    [rp(p) for p in rng.sample(names, 3)], "b", anchor.index
                )
            elif operation == "remove":
                ap.remove_paths(
                    [rp(p) for p in rng.sample(names, 3)], "b", strict=False
                )

            gone = before - set(paths_of(ap))
            for frame in frames:
                frame[1] = [p for p in frame[1] if p not in gone]
            current = paths_of(ap)
            assert ap.memo == set(current)
            for anchor, preexisting in frames:
                assert current[: anchor.index] == preexisting


class TestGlobStaticFile:
    @pytest.fixture
    def addon(self, tmp_path):
        static = tmp_path / "an_addon" / "static"
        (static / "src").mkdir(parents=True)
        (static / "src" / "a.js").write_text("a")
        (static / "src" / "b.scss").write_text("b")
        (static / "src" / "notes.md").write_text("skip me")
        (static / "src" / "LICENSE").write_text("no extension")
        return static

    def test_only_asset_extensions_are_returned(self, addon):
        found = [
            Path(p).name
            for p, _m in _get_static_files(str(addon / "src" / "*"), str(addon))
        ]
        assert found == ["a.js", "b.scss"]

    def test_results_are_sorted_for_deterministic_bundles(self, addon):
        (addon / "src" / "z.js").write_text("z")
        (addon / "src" / "0.js").write_text("0")
        found = [
            p for p, _m in _get_static_files(str(addon / "src" / "*.js"), str(addon))
        ]
        assert found == sorted(found)

    def test_a_missing_literal_yields_nothing(self, addon):
        assert _get_static_files(str(addon / "src" / "nope.js"), str(addon)) == []

    def test_a_symlink_landing_inside_is_followed_and_reported_real(self, addon):
        (addon / "src" / "linked.js").symlink_to(addon / "src" / "a.js")
        found = [
            p
            for p, _m in _get_static_files(str(addon / "src" / "linked.js"), str(addon))
        ]
        assert found == [str(addon / "src" / "a.js")]

    def test_a_symlink_landing_outside_is_refused(self, addon, tmp_path, caplog):
        outside = tmp_path / "elsewhere"
        outside.mkdir()
        (outside / "secret.js").write_text("s")
        (addon / "src" / "escape").symlink_to(outside)
        assert (
            _get_static_files(str(addon / "src" / "escape" / "*.js"), str(addon)) == []
        )
        assert any("links out of" in record.getMessage() for record in caplog.records)

    def test_a_link_and_its_target_collapse_to_one_entry(self, addon):
        (addon / "src" / "linked.js").symlink_to(addon / "src" / "a.js")
        found = _get_static_files(str(addon / "src" / "*.js"), str(addon))
        assert [p for p, _m in found] == [str(addon / "src" / "a.js")]

    def test_the_containment_memo_is_keyed_by_root(self, addon, tmp_path):
        memo: dict[tuple[str, str], bool] = {}
        directory = str(addon / "src")
        assert _is_reachable_without_symlink(directory, str(addon), memo)
        other_root = str(tmp_path / "another_addon" / "static")
        assert not _is_reachable_without_symlink(directory, other_root, memo)
        assert (str(addon), directory) in memo
        assert (other_root, directory) in memo


class TestWalkStructure:
    def test_a_cycle_is_reported_as_the_path_that_closes_it(self):
        walk = make_walk(
            {
                "a.one": [("include", None, "a.two")],
                "a.two": [("include", None, "a.three")],
                "a.three": [("include", None, "a.one")],
            }
        )
        with pytest.raises(ValueError, match="Circular assets bundle declaration") as e:
            walk.walk("a.one")
        assert "a.one > a.two > a.three > a.one" in str(e.value)

    def test_a_bundle_included_twice_contributes_once(self):
        walk = make_walk(
            {
                "a.root": [
                    ("include", None, "a.leaf"),
                    ("append", None, "/mid.js"),
                    ("include", None, "a.leaf"),
                ],
                "a.leaf": [("append", None, "/leaf.js")],
            }
        )
        walk.walk("a.root")
        assert paths_of(walk.paths) == ["/leaf.js", "/mid.js"]

    def test_an_unknown_directive_names_itself(self):
        walk = make_walk({"a.root": [("teleport", None, "/x.js")]})
        with pytest.raises(AssetDirectiveError, match="teleport"):
            walk.walk("a.root")

    def test_a_failing_directive_names_its_declaration_and_bundle(self):
        walk = make_walk({"a.root": [("after", "/absent.js", "/new.js")]})
        with pytest.raises(AssetDirectiveError) as e:
            walk.walk("a.root")
        assert "probe after '/new.js'" in str(e.value)
        assert "declared for bundle 'a.root'" in str(e.value)

    def test_attribution_happens_once_across_includes(self):
        walk = make_walk(
            {
                "a.outer": [("include", None, "a.inner")],
                "a.inner": [("before", "/absent.js", "/new.js")],
            }
        )
        with pytest.raises(AssetDirectiveError) as e:
            walk.walk("a.outer")
        assert str(e.value).count("raised by") == 1
        assert "a.inner" in str(e.value)


class TestPrependAnchorInWalk:
    def test_prepend_in_included_bundle_after_a_remove(self):
        walk = make_walk(
            {
                "t.outer": [
                    ("append", None, "/a.js"),
                    ("append", None, "/b.js"),
                    ("include", None, "t.inner"),
                ],
                "t.inner": [
                    ("remove", None, "/a.js"),
                    ("append", None, "/c.js"),
                    ("prepend", None, "/d.js"),
                ],
            }
        )
        walk.walk("t.outer")
        assert paths_of(walk.paths) == ["/b.js", "/d.js", "/c.js"]

    def test_prepend_in_included_bundle_without_a_remove(self):
        walk = make_walk(
            {
                "t.outer": [
                    ("append", None, "/a.js"),
                    ("append", None, "/b.js"),
                    ("include", None, "t.inner"),
                ],
                "t.inner": [("append", None, "/c.js"), ("prepend", None, "/d.js")],
            }
        )
        walk.walk("t.outer")
        assert paths_of(walk.paths) == ["/a.js", "/b.js", "/d.js", "/c.js"]

    def test_prepend_stays_ahead_of_earlier_prepends(self):
        walk = make_walk(
            {
                "t.root": [
                    ("append", None, "/a.js"),
                    ("prepend", None, "/b.js"),
                    ("prepend", None, "/c.js"),
                ]
            }
        )
        walk.walk("t.root")
        assert paths_of(walk.paths) == ["/c.js", "/b.js", "/a.js"]

    def test_nested_includes_each_prepend_into_their_own_segment(self):
        walk = make_walk(
            {
                "t.a": [
                    ("append", None, "/a.js"),
                    ("include", None, "t.b"),
                    ("prepend", None, "/pa.js"),
                ],
                "t.b": [
                    ("append", None, "/b.js"),
                    ("include", None, "t.c"),
                    ("prepend", None, "/pb.js"),
                ],
                "t.c": [("append", None, "/c.js"), ("prepend", None, "/pc.js")],
            }
        )
        walk.walk("t.a")
        assert paths_of(walk.paths) == [
            "/pa.js",
            "/a.js",
            "/pb.js",
            "/b.js",
            "/pc.js",
            "/c.js",
        ]

    def test_prepend_in_root_bundle_after_a_remove(self):
        walk = make_walk(
            {
                "t.root": [
                    ("append", None, "/a.js"),
                    ("append", None, "/b.js"),
                    ("remove", None, "/a.js"),
                    ("prepend", None, "/c.js"),
                ]
            }
        )
        walk.walk("t.root")
        assert paths_of(walk.paths) == ["/c.js", "/b.js"]


class TestReplaceDirective:
    def _run(self, seed, target, sources):
        walk = make_walk(
            {"b1": [("replace", "TARGET", "SOURCE")]},
            resolve=resolver_for({"TARGET": [target], "SOURCE": sources}),
            seed=seed,
            seed_bundle="b1",
        )
        walk.walk("b1")
        return walk

    def test_source_already_present_is_moved_not_stranded(self):
        walk = self._run(["/a", "/b", "/c"], "/c", ["/a"])
        assert paths_of(walk.paths) == ["/b", "/a"]
        assert "/c" not in walk.paths.memo

    def test_new_source_takes_the_target_slot(self):
        assert paths_of(self._run(["/a", "/b", "/c"], "/c", ["/d"]).paths) == [
            "/a",
            "/b",
            "/d",
        ]

    def test_replacing_a_file_by_itself_keeps_it(self):
        walk = self._run(["/a", "/b", "/c"], "/c", ["/c"])
        assert paths_of(walk.paths) == ["/a", "/b", "/c"]

    def test_an_empty_source_removes_the_target(self):
        walk = self._run(["/a", "/b", "/c"], "/b", [])
        assert paths_of(walk.paths) == ["/a", "/c"]

    def test_sources_land_in_source_order(self):
        walk = self._run(["/a", "/b", "/T"], "/T", ["/a", "/x", "/b", "/y"])
        assert paths_of(walk.paths) == ["/a", "/x", "/b", "/y"]

    def test_a_glob_source_containing_the_target_keeps_it_last(self):
        walk = self._run(["/T", "/c"], "/T", ["/n1", "/T", "/n2"])
        assert paths_of(walk.paths) == ["/n1", "/n2", "/T", "/c"]


class TestGlobTargets:
    def _run(self, directive, seed, targets, sources):
        walk = make_walk(
            {"b1": [(directive, "/f*.js", "SOURCE")]},
            resolve=resolver_for({"/f*.js": targets, "SOURCE": sources}),
            seed=seed,
            seed_bundle="b1",
        )
        walk.walk("b1")
        return paths_of(walk.paths)

    def test_every_matched_target_is_replaced(self):
        got = self._run(
            "replace",
            ["/f1.js", "/f2.js", "/keep.js"],
            ["/f1.js", "/f2.js"],
            ["/new.js"],
        )
        assert got == ["/new.js", "/keep.js"]

    def test_matches_absent_from_the_bundle_are_tolerated(self):
        got = self._run(
            "replace", ["/f2.js", "/keep.js"], ["/f1.js", "/f2.js"], ["/new.js"]
        )
        assert got == ["/new.js", "/keep.js"]

    def test_a_matched_target_that_is_also_a_source_survives(self):
        got = self._run(
            "replace",
            ["/f1.js", "/f2.js", "/keep.js"],
            ["/f1.js", "/f2.js"],
            ["/new.js", "/f2.js"],
        )
        assert got == ["/new.js", "/f2.js", "/keep.js"]

    def test_no_matched_target_present_still_raises(self):
        with pytest.raises(AssetDirectiveError, match=re.escape("/f1.js")):
            self._run("replace", ["/keep.js"], ["/f1.js", "/f2.js"], ["/new.js"])

    def test_before_anchors_on_the_first_resolved_target_the_bundle_holds(self):
        got = self._run(
            "before",
            ["/f2.js", "/f1.js", "/keep.js"],
            ["/f1.js", "/f2.js"],
            ["/new.js"],
        )
        assert got == ["/f2.js", "/new.js", "/f1.js", "/keep.js"]

    def test_after_skips_matches_the_bundle_does_not_carry(self):
        got = self._run(
            "after", ["/f2.js", "/keep.js"], ["/f1.js", "/f2.js"], ["/new.js"]
        )
        assert got == ["/f2.js", "/new.js", "/keep.js"]


class TestPositioningIsNotMoving:
    def _run(self, directive, target, source, caplog, *directives):
        walk = make_walk(
            {"b1": [*directives, (directive, target, source)]},
            seed=["/a", "/b", "/c"],
            seed_bundle="b1",
        )
        walk.walk("b1")
        return paths_of(walk.paths), " ".join(r.getMessage() for r in caplog.records)

    @pytest.mark.parametrize(
        ("directive", "target", "source"),
        [("after", "/c", "/a"), ("before", "/a", "/c")],
    )
    def test_a_stranded_source_warns_and_does_not_move(
        self, directive, target, source, caplog
    ):
        """The source sits on the wrong side of its target and stays there."""
        paths, log = self._run(directive, target, source, caplog)
        assert paths == ["/a", "/b", "/c"]
        assert "already present" in log
        assert f"{directive} only places new files" in log

    def test_a_prepend_of_a_file_this_frame_placed_past_its_anchor_warns(self, caplog):
        paths, log = self._run(
            "prepend",
            None,
            "/y",
            caplog,
            ("append", None, "/x"),
            ("append", None, "/y"),
        )
        assert paths == ["/a", "/b", "/c", "/x", "/y"]
        assert "already present" in log
        assert "prepend only places new files" in log

    @pytest.mark.parametrize(
        ("directive", "target", "source"),
        [("after", "/a", "/c"), ("before", "/c", "/a"), ("prepend", None, "/c")],
    )
    def test_a_source_already_where_the_directive_wants_it_is_silent(
        self, directive, target, source, caplog
    ):
        paths, log = self._run(directive, target, source, caplog)
        assert paths == ["/a", "/b", "/c"]
        assert not log

    def test_a_new_source_is_silent(self, caplog):
        paths, log = self._run("prepend", None, "/new", caplog)
        assert paths == ["/a", "/b", "/c", "/new"], (
            "the anchor is the start of THIS frame's segment; the seed was "
            "contributed before the frame opened, so prepending goes after it"
        )
        assert not log

    def test_appending_what_another_addon_contributed_stays_silent(self, caplog):
        paths, log = self._run("append", None, "/a", caplog)
        assert paths == ["/a", "/b", "/c"]
        assert not log


class TestRemoveDirectiveSemantics:
    def _run(self, path_def, resolved, caplog):
        walk = make_walk(
            {"b1": [("remove", None, path_def)]},
            resolve=resolver_for({path_def: resolved}),
            seed=["/web/a.js", "/web/b.js"],
            seed_bundle="b1",
        )
        walk.walk("b1")
        return paths_of(walk.paths), " ".join(r.getMessage() for r in caplog.records)

    def test_a_glob_remove_tolerates_absent_matches(self, caplog):
        paths, log = self._run("/web/**/*.js", ["/web/b.js", "/web/zzz.js"], caplog)
        assert paths == ["/web/a.js"]
        assert not log

    def test_a_glob_matching_nothing_in_the_bundle_is_a_silent_noop(self, caplog):
        paths, log = self._run("/web/**/*.dark.scss", ["/web/x.dark.scss"], caplog)
        assert paths == ["/web/a.js", "/web/b.js"]
        assert not log

    def test_a_literal_remove_of_an_absent_path_raises(self, caplog):
        with pytest.raises(AssetDirectiveError):
            self._run("/web/absent.js", ["/web/absent.js"], caplog)

    def test_a_path_resolving_to_nothing_warns_instead_of_raising(self, caplog):
        paths, log = self._run("/web/gone.js", [], caplog)
        assert paths == ["/web/a.js", "/web/b.js"]
        assert "had no effect" in log

    def test_a_remove_that_finds_its_file_is_silent(self, caplog):
        paths, log = self._run("/web/a.js", ["/web/a.js"], caplog)
        assert paths == ["/web/b.js"]
        assert not log

    def test_an_append_resolving_to_nothing_does_not_warn(self, caplog):
        walk = make_walk(
            {"b1": [("append", None, "/web/absent/**/*.js")]},
            resolve=resolver_for({"/web/absent/**/*.js": []}),
        )
        walk.walk("b1")
        assert paths_of(walk.paths) == []
        assert not caplog.records


class TestTargetlessDirectives:
    def test_a_positional_directive_without_a_target_is_skipped(self, caplog):
        walk = make_walk(
            {"b1": [("after", None, "/x.js")]}, seed=["/a"], seed_bundle="b1"
        )
        walk.walk("b1")
        assert paths_of(walk.paths) == ["/a"]
        assert "has no target" in " ".join(r.getMessage() for r in caplog.records)

    def test_a_target_resolving_to_nothing_is_skipped(self, caplog):
        walk = make_walk(
            {"b1": [("after", "/gone.js", "/x.js")]},
            resolve=resolver_for({"/gone.js": []}),
            seed=["/a"],
            seed_bundle="b1",
        )
        walk.walk("b1")
        assert paths_of(walk.paths) == ["/a"]
        assert "resolved to nothing" in " ".join(r.getMessage() for r in caplog.records)


class TestResolvedPath:
    def test_a_filesystem_path_is_not_external(self):
        assert not ResolvedPath("/web/a.js", "/abs/a.js", 1.0).is_external

    def test_an_attachment_fallback_is_not_external(self):
        assert not ResolvedPath("/web/a.js", None, None).is_external

    def test_the_sentinel_marks_an_external_url(self):
        from odoo.tools.assets.constants import EXTERNAL_ASSET

        assert ResolvedPath("http://x/a.js", EXTERNAL_ASSET, -1).is_external


def test_the_leaf_module_stays_framework_free():
    source = Path(__file__).resolve().parents[1] / "ir_asset_paths.py"
    text = source.read_text()
    for forbidden in ("from odoo import", "models.Model", "odoo.modules", "odoo.api"):
        assert forbidden not in text, f"{forbidden!r} leaked into the leaf module"
