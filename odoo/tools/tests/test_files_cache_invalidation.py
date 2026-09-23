import pathlib
import tempfile
import unittest

from odoo.modules.module import initialize_sys_path
from odoo.tools import file_path, files

import odoo.addons


def _addons_dir(marker: str) -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp())
    module = root / "zz_cache_probe"
    module.mkdir()
    (module / "__manifest__.py").write_text("{'name': 'zz'}", encoding="utf-8")
    (module / "thing.txt").write_text(marker, encoding="utf-8")
    return root


class TestSwappingTheAddonsPath(unittest.TestCase):
    def setUp(self):
        self._saved = list(odoo.addons.__path__)
        self.addCleanup(self._restore)

    def _restore(self):
        odoo.addons.__path__[:] = self._saved
        files.clear_caches()

    @staticmethod
    def _read() -> str:
        return pathlib.Path(file_path("zz_cache_probe/thing.txt")).read_text(
            encoding="utf-8"
        )

    def test_a_swap_without_clearing_serves_the_previous_answer(self):
        first, second = _addons_dir("FIRST"), _addons_dir("SECOND")
        odoo.addons.__path__[:] = [str(first)]
        files.clear_caches()
        self.assertEqual(self._read(), "FIRST")

        odoo.addons.__path__[:] = [str(second)]
        self.assertEqual(self._read(), "FIRST", "precondition: the cache is warm")

        files.clear_caches()
        self.assertEqual(self._read(), "SECOND")

    def test_clear_caches_empties_every_path_cache(self):
        odoo.addons.__path__[:] = [str(_addons_dir("X"))]
        files.clear_caches()
        self._read()
        self.assertTrue(files._file_path_resolved.cache_info().currsize)
        files.clear_caches()
        for cache in (
            files._file_path_resolved,
            files._addons_dir_paths,
        ):
            with self.subTest(cache=cache.__wrapped__.__name__):
                self.assertEqual(cache.cache_info().currsize, 0)


class TestInitializeSysPathDoesNotThrashTheCache(unittest.TestCase):
    def test_an_unchanged_path_keeps_the_cache_warm(self):
        initialize_sys_path()
        file_path("base/__manifest__.py")
        warm = files._file_path_resolved.cache_info().currsize
        self.assertTrue(warm)
        initialize_sys_path()
        initialize_sys_path()
        self.assertEqual(files._file_path_resolved.cache_info().currsize, warm)


if __name__ == "__main__":
    unittest.main()
