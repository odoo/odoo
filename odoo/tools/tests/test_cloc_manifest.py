import pathlib
import tempfile
import unittest

from odoo.tools.cloc import Cloc

_LITERAL = '{"name": "m", "cloc_exclude": ["secret.py"]}'
_COMPUTED = '{"name": "m", "cloc_exclude": ["secret.py"], "version": "1." + "0"}'
_BROKEN = '{"name": "m",'


def _module(manifest: str | None) -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp()) / "mymod"
    (root / "tests").mkdir(parents=True)
    if manifest is not None:
        (root / "__manifest__.py").write_text(manifest, encoding="utf-8")
    (root / "billable.py").write_text("a = 1\nb = 2\nc = 3\n", encoding="utf-8")
    (root / "secret.py").write_text("x = 1\n" * 40, encoding="utf-8")
    (root / "tests" / "test_x.py").write_text("y = 1\n" * 20, encoding="utf-8")
    return root


def _count(manifest: str | None) -> Cloc:
    cloc = Cloc()
    cloc.count_path(str(_module(manifest)))
    return cloc


class TestManifestExclusions(unittest.TestCase):
    def test_a_literal_manifest_applies_its_exclusions(self):
        cloc = _count(_LITERAL)
        self.assertEqual(cloc.code["mymod"], 3)
        self.assertFalse(cloc.errors)

    def test_an_unreadable_manifest_loses_the_exclusions_it_could_not_read(self):
        readable = _count(_LITERAL).code["mymod"]
        unreadable = _count(_COMPUTED).code["mymod"]
        self.assertGreater(unreadable, readable)

    def test_an_unreadable_manifest_is_reported_not_swallowed(self):
        for label, manifest in (("computed value", _COMPUTED), ("broken", _BROKEN)):
            with self.subTest(manifest=label):
                cloc = _count(manifest)
                self.assertIn("mymod", cloc.errors)
                reported = " ".join(cloc.errors["mymod"].values())
                self.assertIn("exclusions ignored", reported)

    def test_an_absent_manifest_is_not_an_error(self):
        cloc = _count(None)
        self.assertFalse(cloc.errors)
        self.assertTrue(cloc.code["mymod"])

    def test_the_report_surfaces_the_error(self):
        cloc = _count(_COMPUTED)
        self.assertIn("Errors", cloc.report())
        self.assertIn("exclusions ignored", cloc.report())


class TestManifestExclusionShapes(unittest.TestCase):
    def test_a_single_string_exclusion_is_one_pattern(self):
        cloc = _count('{"name": "m", "cloc_exclude": "secret.py"}')
        self.assertEqual(cloc.code["mymod"], 3)
        self.assertFalse(cloc.errors)

    def test_a_string_holding_a_path_does_not_abort_the_count(self):
        root = _module('{"name": "m", "cloc_exclude": "sub/secret.py"}')
        (root / "sub").mkdir()
        (root / "sub" / "secret.py").write_text("z = 1\n" * 9, encoding="utf-8")
        cloc = Cloc()
        cloc.count_path(str(root))
        self.assertEqual(cloc.code["mymod"], 43)
        self.assertFalse(cloc.errors)

    def test_an_absolute_pattern_is_reported_and_the_rest_still_applies(self):
        cloc = _count('{"name": "m", "cloc_exclude": ["/etc/*", "secret.py"]}')
        self.assertEqual(cloc.code["mymod"], 3)
        self.assertIn(
            "Invalid exclusion pattern", " ".join(cloc.errors["mymod"].values())
        )
        self.assertIn("/etc/*", " ".join(cloc.errors["mymod"]))

    def test_a_non_string_pattern_is_reported(self):
        cloc = _count('{"name": "m", "cloc_exclude": [None, 3, "secret.py"]}')
        self.assertEqual(cloc.code["mymod"], 3)
        self.assertEqual(len(cloc.errors["mymod"]), 1)

    def test_a_parent_directory_pattern_is_still_refused(self):
        with self.assertRaises(ValueError):
            _count('{"name": "m", "cloc_exclude": "../x.py"}')


if __name__ == "__main__":
    unittest.main()
