import os
import shutil
import stat
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from odoo.tools import config
from odoo.tools.assets import esbuild
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

    def test_a_base_others_can_write_is_not_trusted(self):
        base = self.data_dir / "esbuild-roots"
        base.mkdir(parents=True)
        base.chmod(0o777)
        node_path = self._node_path()
        self.assertTrue(node_path.is_relative_to(self.private))
        self.assertEqual(self._resolves_to(node_path), self.web_src.resolve())

    def test_a_base_owned_by_someone_else_is_not_trusted(self):
        (self.data_dir / "esbuild-roots").mkdir(parents=True, mode=0o700)
        with mock.patch.object(esbuild.os, "getuid", return_value=os.getuid() + 1):
            node_path = self._node_path()
        self.assertTrue(node_path.is_relative_to(self.private))


class TestARootInUseIsNeverReplaced(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        target = self.tmp / "src"
        target.mkdir()
        self.roots = {f"@addon{i}": target for i in range(600)}
        self.base = self.tmp / "esbuild-roots"
        self.base.mkdir(mode=0o700)

    def test_a_root_published_while_this_caller_staged_is_kept(self):
        published = self.base / "digest"
        write = esbuild._write_resolution_root
        handed_out = []

        def peer_publishes_first(root_dir, roots):
            if root_dir != published and not handed_out:
                handed_out.append(write(published, roots).stat().st_ino)
            return write(root_dir, roots)

        with mock.patch.object(esbuild, "_write_resolution_root", peer_publishes_first):
            root = esbuild._shared_resolution_root(self.base, "digest", self.roots)
        self.assertEqual(root.stat().st_ino, handed_out[0])

    def test_concurrent_first_builds_share_one_root(self):
        callers = 4
        for stagger in (0.01, 0.0) * 3:
            base = Path(tempfile.mkdtemp(dir=self.base))
            barrier = threading.Barrier(callers)
            outcomes = []

            def compile_with(delay, base=base, barrier=barrier, outcomes=outcomes):
                barrier.wait()
                time.sleep(delay)
                try:
                    root = esbuild._shared_resolution_root(base, "digest", self.roots)
                    inode = root.stat().st_ino
                    time.sleep(0.05)
                    still = root.stat().st_ino == inode
                except OSError as exc:
                    outcomes.append(type(exc).__name__)
                    return
                outcomes.append((inode, still))

            threads = [
                threading.Thread(target=compile_with, args=(k * stagger,))
                for k in range(callers)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            with self.subTest(stagger=stagger):
                self.assertEqual(len(set(outcomes)), 1, outcomes)
                self.assertTrue(outcomes[0][1], "a caller's root vanished under it")


if __name__ == "__main__":
    unittest.main()
