import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from odoo.tools.files import _addons_dir_paths, clear_caches, file_path

import odoo.addons


class _AddonsRoot:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.addons = root / "addons"
        self.outside = root / "outside"
        (self.addons / "mymod" / "static").mkdir(parents=True)
        self.outside.mkdir()
        (self.addons / "mymod" / "static" / "ok.txt").write_text("ok")
        (self.addons / "mymod" / "static" / "pic.PNG").write_text("img")
        (self.outside / "secret.txt").write_text("secret")
        self.escape = self.addons / "mymod" / "escape"
        self.escape.symlink_to(self.outside, target_is_directory=True)

    def __enter__(self):
        self._saved_path = list(odoo.addons.__path__)
        self._saved_mod = sys.modules.pop("odoo.addons.mymod", None)
        odoo.addons.__path__[:] = [str(self.addons)]
        clear_caches()
        return self

    def __exit__(self, *exc):
        odoo.addons.__path__[:] = self._saved_path
        if self._saved_mod is not None:
            sys.modules["odoo.addons.mymod"] = self._saved_mod
        clear_caches()
        self.tmp.cleanup()


class TestFilePathContainment(unittest.TestCase):
    def test_resolves_a_file_inside_addons(self):
        with _AddonsRoot() as r:
            got = file_path("mymod/static/ok.txt")
            self.assertEqual(Path(got).read_text(encoding="utf-8"), "ok")
            self.assertTrue(Path(got).is_relative_to(r.addons))

    def test_dotdot_traversal_is_rejected(self):
        with _AddonsRoot():
            with self.assertRaises(FileNotFoundError):
                file_path("mymod/../../outside/secret.txt")

    def test_deep_dotdot_traversal_is_rejected(self):
        with _AddonsRoot():
            with self.assertRaises(FileNotFoundError):
                file_path("mymod/static/../../../outside/secret.txt")

    def test_symlink_escaping_addons_is_rejected(self):
        with _AddonsRoot() as r:
            self.assertTrue(r.escape.is_symlink())
            self.assertTrue((r.escape / "secret.txt").exists())
            with self.assertRaises(FileNotFoundError):
                file_path("mymod/escape/secret.txt")

    def test_absolute_path_outside_addons_is_rejected(self):
        with _AddonsRoot() as r:
            with self.assertRaises(FileNotFoundError):
                file_path(str(r.outside / "secret.txt"))

    def test_absolute_path_inside_addons_is_accepted(self):
        with _AddonsRoot() as r:
            target = r.addons / "mymod" / "static" / "ok.txt"
            self.assertEqual(
                Path(file_path(str(target))).read_text(encoding="utf-8"), "ok"
            )

    def test_an_absolute_symlink_escaping_addons_is_rejected(self):
        with _AddonsRoot() as r:
            with self.assertRaises(FileNotFoundError):
                file_path(str(r.escape / "secret.txt"))

    def test_an_absolute_path_resolves_once_whatever_the_number_of_addons_dirs(self):
        with _AddonsRoot() as r:
            odoo.addons.__path__[:] = [
                str(r.outside),
                str(r.outside),
                str(r.addons),
            ]
            clear_caches()
            target = r.addons / "mymod" / "static" / "ok.txt"
            with unittest.mock.patch("os.path.realpath", wraps=os.path.realpath) as rp:
                self.assertEqual(file_path(str(target)), str(target))
            self.assertEqual(
                sum(1 for c in rp.call_args_list if str(c.args[0]) == str(target)),
                1,
                "resolved once (Path.resolve), not once more per addons dir",
            )

    def test_missing_file_raises(self):
        with _AddonsRoot():
            with self.assertRaises(FileNotFoundError):
                file_path("mymod/static/nope.txt")


class TestFilePathExtensionFilter(unittest.TestCase):
    def test_matching_extension_passes(self):
        with _AddonsRoot():
            self.assertTrue(file_path("mymod/static/ok.txt", filter_ext=(".txt",)))

    def test_non_matching_extension_raises_valueerror(self):
        with _AddonsRoot():
            with self.assertRaises(ValueError):
                file_path("mymod/static/ok.txt", filter_ext=(".png",))

    def test_extension_match_is_case_insensitive(self):
        with _AddonsRoot():
            self.assertTrue(file_path("mymod/static/pic.PNG", filter_ext=(".png",)))

    def test_default_filter_accepts_anything(self):
        with _AddonsRoot():
            self.assertTrue(file_path("mymod/static/ok.txt"))


class TestAddonsDirMemoisation(unittest.TestCase):
    def test_same_dir_is_memoised(self):
        _addons_dir_paths.cache_clear()
        with tempfile.TemporaryDirectory() as d:
            first = _addons_dir_paths(d)
            second = _addons_dir_paths(d)
            self.assertIs(first, second)
            self.assertEqual(_addons_dir_paths.cache_info().hits, 1)

    def test_distinct_dirs_do_not_alias(self):
        _addons_dir_paths.cache_clear()
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            self.assertNotEqual(_addons_dir_paths(a), _addons_dir_paths(b))

    def test_resolved_form_collapses_symlinks(self):
        _addons_dir_paths.cache_clear()
        with tempfile.TemporaryDirectory() as d:
            real = Path(d) / "real"
            real.mkdir()
            link = Path(d) / "link"
            link.symlink_to(real, target_is_directory=True)
            normalised, resolved = _addons_dir_paths(str(link))
            self.assertEqual(str(normalised), os.path.normcase(str(link)))
            self.assertEqual(resolved, real.resolve())


if __name__ == "__main__":
    unittest.main()
