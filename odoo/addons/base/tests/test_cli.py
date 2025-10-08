import argparse
import os
import re
import subprocess as sp
import sys
import unittest
from contextlib import redirect_stdout
from io import BytesIO, TextIOWrapper
from pathlib import Path

from odoo.cli.command import commands, load_addons_commands, load_internal_commands
from odoo.cli.i18n import I18n
from odoo.tests import BaseCase, TransactionCase, tagged
from odoo.tests.common import Like
from odoo.tools import config, file_path


@tagged('at_install', '-post_install')  # LEGACY at_install
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
        for name in ('bonbon', 'café'):
            with self.subTest(name):
                command_output = self.run_command(name, check=False).stderr.strip()
                self.assertEqual(
                    command_output,
                    f"Unknown command '{name}'.\n"
                    "Use 'odoo-bin --help' to see the list of available commands."
                )

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

    def test_help_subcommand(self):
        """Just execute the help for each internal sub-command"""
        load_internal_commands()
        for name in commands:
            with self.subTest(command=name):
                self.run_command(name, '--help', timeout=10)

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
        self.assertFalse(shell.wait(), "exited with a non 0 code")

        # we skip local variables as they differ based on configuration (e.g.: if a database is specified or not)
        lines = [line for line in shell.stdout.read().splitlines() if line.startswith('>>>')]
        self.assertEqual(lines, [">>> Hello from Python!", '>>> '])


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestCommandUsingDb(TestCommand, TransactionCase):

    def test_i18n_export(self):
        reader_mock_result = [
            ('base', 'code', 'addons/template_inheritance.py', 331,
             "Invalid position attribute: '%s'", '', ('odoo-python',)),
            ('base', 'code', 'addons/template_inheritance.py', 341,
             "Element '%s' cannot be located in parent view", '', ('odoo-python',)),
        ]
        expected_text = [
            "# Translation of Odoo Server.",
            "# This file contains the translation of the following modules:",
            '# \t* base',
            "#",
            'msgid ""',
            'msgstr ""',
            Like('"Project-Id-Version: ..."'),
            '"Report-Msgid-Bugs-To: \\n"',
            Like('"POT-Creation-Date: ...'),
            Like('"PO-Revision-Date: ...'),
            '"Last-Translator: \\n"',
            '"Language-Team: \\n"',
            '"MIME-Version: 1.0\\n"',
            '"Content-Type: text/plain; charset=UTF-8\\n"',
            '"Content-Transfer-Encoding: \\n"',
            '"Plural-Forms: \\n"',
            '#. module: base',
            '#. odoo-python',
            '#: code:addons/template_inheritance.py:0',
            'msgid "Element \'%s\' cannot be located in parent view"',
            'msgstr ""',
            '#. module: base',
            '#. odoo-python',
            '#: code:addons/template_inheritance.py:0',
            'msgid "Invalid position attribute: \'%s\'"',
            'msgstr ""',
        ]

        def mock_result():
            def inner(env, modules, lang):
                return reader_mock_result
            return inner

        with unittest.mock.patch('odoo.tools.translate.TranslationModuleReader', new_callable=mock_result):
            output_buffer = BytesIO()
            output_wrapper = TextIOWrapper(output_buffer, encoding="utf-8")
            with redirect_stdout(output_wrapper):
                # Do not call ``config.parse_args(...)`` in tests.
                # It would modify the global ``config`` object and disable
                # the ``--test-enable`` flag, breaking the ``at-install``
                # CI test build.
                I18n()._export(argparse.Namespace(
                    db_name=self.env.cr.dbname,
                    output='-',
                    modules=['base'],
                    languages=['pot'],
                ))
                output_wrapper.flush()

            actual_text = [
                stripped
                for line in output_buffer.getvalue().decode().splitlines()
                if (stripped := line.strip()) and stripped
            ]
            self.assertEqual(actual_text, expected_text)
