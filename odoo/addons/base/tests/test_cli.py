import re
import sys
import subprocess as sp

from odoo.cli.command import commands, load_addons_commands, load_internal_commands
from odoo.tools import config
from odoo.tests import BaseCase


class TestCommand(BaseCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.odoo_bin = sys.argv[0]
        assert 'odoo-bin' in cls.odoo_bin

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

    def test_docstring(self):
        load_internal_commands()
        load_addons_commands()
        for name, cmd in commands.items():
            self.assertTrue(cmd.__doc__,
                msg=f"Command {name} needs a docstring to be displayed with 'odoo-bin help'")
            self.assertFalse('\n' in cmd.__doc__ or len(cmd.__doc__) > 120,
                msg=f"Command {name}'s docstring format is invalid for 'odoo-bin help'")

    def test_help(self):
        expected = {
            'cloc',
            'db',
            'deploy',
            'help',
            'neutralize',
            'obfuscate',
            'populate',
            'scaffold',
            'server',
            'shell',
            'start',
            'upgrade_code',
        }
        for option in ('help', '-h', '--help'):
            with self.subTest(option=option):
                actual = set()
                for line in self.run_command(option).stdout.splitlines():
                    if line.startswith("   ") and (result := re.search(r'    (\w+)\s+(\w.*)$', line)):
                        actual.add(result.groups()[0])
                self.assertGreaterEqual(actual, expected, msg="Help is not showing required commands")
