# Part of Odoo. See LICENSE file for full copyright and licensing details.

from pathlib import Path

from odoo.modules import Manifest

from .common import LintCase

KNOWN_DATA_MODULES = {'test_data_module'}


class TestDunderinit(LintCase):

    def test_dunderinit(self):
        """ Test that __init__.py exists in Odoo modules, otherwise they won't get packaged"""

        modules_list = [mod for mod in Manifest.all_addon_manifests() if mod.name not in KNOWN_DATA_MODULES]
        self.assertTrue(len(modules_list), "No modules found!")
        for mod in modules_list:
            dunderinit_path = Path(mod.path) / '__init__.py'
            self.assertTrue(dunderinit_path.is_file(), "Missing `__init__.py ` in module %s" % mod)
