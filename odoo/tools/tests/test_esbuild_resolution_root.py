import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path

from odoo.tools import config
from odoo.tools.assets.esbuild import EsbuildCompiler


class TestTheResolutionRootIsNotAPlantableTempDir(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.odoo_root = self.tmp / "checkout"
        self.web_src = self.odoo_root / "addons" / "web" / "static" / "src"
        self.web_src.mkdir(parents=True)
        self.evil = self.tmp / "evil_web"
        self.evil.mkdir()
        self.data_dir = self.tmp / "data"
        self.enterContext(config.patch(data_dir=str(self.data_dir)))
        self.private = self.tmp / "compile"
        self.private.mkdir()

    def _node_path(self) -> Path:
        compiler = EsbuildCompiler("probe", [])
        _kept, node_path = compiler._addon_resolution_root(
            ["--alias:@web=./addons/web/static/src"],
            self.odoo_root,
            str(self.private),
        )
        return Path(node_path)

    def _resolves_to(self, node_path: Path) -> Path:
        return Path(os.path.realpath(node_path / "@web"))

    def test_the_root_lives_under_data_dir(self):
        node_path = self._node_path()
        self.assertEqual(node_path.parent, self.data_dir / "esbuild-roots")
        self.assertEqual(self._resolves_to(node_path), self.web_src.resolve())
        mode = stat.S_IMODE(node_path.parent.stat().st_mode)
        self.assertEqual(mode & 0o077, 0, "the base must be private to its owner")

    def test_a_tampered_entry_is_rebuilt_not_trusted(self):
        node_path = self._node_path()
        (node_path / "@web").unlink()
        (node_path / "@web").symlink_to(self.evil, target_is_directory=True)
        self.assertEqual(self._resolves_to(self._node_path()), self.web_src.resolve())

    def test_a_planted_symlink_in_place_of_the_root_is_replaced(self):
        node_path = self._node_path()
        planted = self.tmp / "planted"
        planted.mkdir()
        (planted / "@web").symlink_to(self.evil, target_is_directory=True)
        for entry in node_path.iterdir():
            entry.unlink()
        node_path.rmdir()
        node_path.symlink_to(planted, target_is_directory=True)
        rebuilt = self._node_path()
        self.assertFalse(rebuilt.is_symlink())
        self.assertEqual(self._resolves_to(rebuilt), self.web_src.resolve())

    def test_an_extra_entry_is_not_carried_along(self):
        node_path = self._node_path()
        (node_path / "@evil").symlink_to(self.evil, target_is_directory=True)
        self.assertFalse((self._node_path() / "@evil").exists())

    def test_an_unwritable_data_dir_falls_back_to_the_compile_s_own_dir(self):
        blocker = self.tmp / "not_a_dir"
        blocker.write_text("")
        with config.patch(data_dir=str(blocker)):
            node_path = self._node_path()
        self.assertTrue(node_path.is_relative_to(self.private))
        self.assertEqual(self._resolves_to(node_path), self.web_src.resolve())


if __name__ == "__main__":
    unittest.main()
