import os
import re
import sys
import subprocess as sp
import unittest
from pathlib import Path

from odoo.cli.command import commands, load_addons_commands, load_internal_commands
from odoo.tools import config, file_path
from odoo.tests import BaseCase, Like

class TestCommand(BaseCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.odoo_bin = Path(__file__).parents[4].resolve() / 'odoo-bin'
        addons_path = config.format('addons_path', config['addons_path'])
        cls.run_args = (sys.executable, cls.odoo_bin, f'--addons-path={addons_path}')

    def run_command(self, *args, check=True, capture_output=True, text=True, **kwargs):
        return sp.run(
            [*self.run_args, *args],
            capture_output=capture_output,
            check=check,
            text=text,
            **kwargs
        )

    def popen_command(self, *args, capture_output=True, text=True, **kwargs):
        if capture_output:
            kwargs['stdout'] = kwargs['stderr'] = sp.PIPE
        return sp.Popen(
            [*self.run_args, *args],
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

    def test_unknown_command(self):
        command_output = self.run_command('bonbon', check=False).stderr.strip()
        self.assertEqual(command_output, "Unknown command 'bonbon'")

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

    @unittest.skipIf(os.name != 'posix', '`os.openpty` only available on POSIX systems')
    def test_shell(self):

        main, child = os.openpty()

        shell = self.popen_command(
            'shell',
            '--shell-interface=python',
            '--shell-file', file_path('base/tests/shell_file.txt'),
            stdin=main,
            close_fds=True,
        )
        with os.fdopen(child, 'w', encoding="utf-8") as stdin_file:
            stdin_file.write(
                'print(message)\n'
                'exit()\n'
            )
        shell.wait()

        self.assertEqual(shell.stdout.read().splitlines(), [
            Like("No environment set..."),
            Like("odoo: <module 'odoo' from '/.../odoo/__init__.py'>"),
            Like("openerp: <module 'odoo' from '/.../odoo/__init__.py'>"),
            ">>> Hello from Python!",
            '>>> '
        ])
