import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from odoo.libs.filesystem.appdirs import site_data_dir, user_data_dir

HOME_DATA = str(Path("~/.local/share").expanduser())


@unittest.skipIf(sys.platform in ("win32", "darwin"), "the XDG branch is POSIX-only")
class TestXdgDataDirs(unittest.TestCase):
    def _user(self, value):
        with mock.patch.dict(os.environ, {"XDG_DATA_HOME": value}):
            return user_data_dir("Odoo", "OpenERP S.A.")

    def _site(self, value):
        with mock.patch.dict(os.environ, {"XDG_DATA_DIRS": value}):
            return site_data_dir("Odoo", "OpenERP S.A.")

    def test_an_absolute_data_home_is_used(self):
        self.assertEqual(self._user("/srv/data"), "/srv/data/Odoo")

    def test_an_unset_data_home_is_the_default(self):
        with mock.patch.dict(os.environ, clear=False):
            os.environ.pop("XDG_DATA_HOME", None)
            self.assertEqual(user_data_dir("Odoo"), f"{HOME_DATA}/Odoo")

    def test_an_empty_data_home_is_the_default_not_the_cwd(self):
        self.assertEqual(self._user(""), f"{HOME_DATA}/Odoo")

    def test_a_relative_data_home_is_ignored(self):
        self.assertEqual(self._user("relative/dir"), f"{HOME_DATA}/Odoo")

    def test_site_dirs_take_the_first_absolute_entry(self):
        self.assertEqual(self._site("rel:/opt/share/:/usr/share"), "/opt/share/Odoo")

    def test_empty_site_dirs_are_the_default(self):
        self.assertEqual(self._site(""), "/usr/local/share/Odoo")


if __name__ == "__main__":
    unittest.main()
