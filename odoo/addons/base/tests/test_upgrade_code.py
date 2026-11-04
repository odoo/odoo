import subprocess as sp
import sys
from os.path import join as opj, realpath

from odoo.tools import config
from odoo.tests import BaseCase


class TestCommand(BaseCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.odoo_bin = realpath(opj(__file__, '../../../../../odoo-bin'))

    def run_command(self, *args, check=True, capture_output=True, text=True, **kwargs):
        return sp.run(
            [
                sys.executable,
                self.odoo_bin,
                f'--addons-path={config["addons_path"]}',
                *args,
            ],
            capture_output=capture_output,
            check=check,
            text=text,
            **kwargs
        )

    def test_upgrade_code_example(self):
        proc = self.run_command('upgrade_code', '--script', '17.5-00-example', '--dry-run')
        self.assertFalse(proc.stdout, "there should be no file modified by the example script")
        self.assertFalse(proc.stderr)

    def test_upgrade_code_help(self):
        proc = self.run_command('upgrade_code', '--help')
        self.assertIn("usage: ", proc.stdout)
        self.assertIn("Rewrite the entire source code", proc.stdout)
        self.assertFalse(proc.stderr)

    def test_upgrade_code_standalone(self):
        from odoo.cli import upgrade_code  # noqa: PLC0415
        proc = sp.run(
            [sys.executable, upgrade_code.__file__, '--help'],
            check=True, capture_output=True, text=True
        )
        self.assertIn("usage: ", proc.stdout)
        self.assertIn("Rewrite the entire source code", proc.stdout)
        self.assertFalse(proc.stderr)
