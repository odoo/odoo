import io
import logging
import os
import re
import subprocess as sp
import sys
import textwrap
import time
import unittest
from pathlib import Path

from odoo.cli.command import commands, load_addons_commands, load_internal_commands
from odoo.tests import BaseCase, TransactionCase
from odoo.tools import config, file_path


def select_not_available():
    return os.name != 'posix' and sys.version_info < (3, 12)


_logger = logging.getLogger(__name__)
SELECT_MESSAGE = "os.set_blocking on files only available in windows starting 3.12"


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
            **kwargs,
        )

    def popen_command(self, *args, capture_output=True, text=True, **kwargs):
        if capture_output:
            kwargs['stdout'] = kwargs['stderr'] = sp.PIPE
        return sp.Popen(
            [*self.run_args, *args],
            text=text,
            **kwargs,
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


class TestCommandUsingDb(TestCommand, TransactionCase):

    def _expect(self, command_args, expected_text, maxlen=None, timeout=15, stream=sys.stdout):
        """ Wait for a process that takes a long time to run, then compare
            the first part of the result. We are only interested in making
            sure it starts correctly.

            This test only asserts the first few lines and then SIGTERM
            the process. We took the challenge to write a cross-platform
            test, the lack of a select-like API for Windows makes the code
            a bit complicated. Sorry :/
        """

        assert stream in (sys.stdout, sys.stderr)
        maxlen = maxlen or len(expected_text)
        buffer = io.BytesIO()

        # ensure we get a io.FileIO and not a buffer or text
        proc = self.popen_command(*command_args, text=False, bufsize=0)
        stream = proc.stdout if stream == sys.stdout else proc.stderr
        os.set_blocking(stream.fileno(), False)

        # Feed the buffer for maximum timeout seconds.
        maxtime = time.monotonic() + timeout
        while buffer.tell() < maxlen and time.monotonic() < maxtime:
            if chunk := stream.read(maxlen - buffer.tell()):
                buffer.write(chunk)
            else:
                # would had loved to use select() for its timeout, but
                # select doesn't work on files on windows, use a flat
                # sleep instead: not great, not terrible.
                time.sleep(.1)

        proc.terminate()
        try:
            proc.wait(timeout=5)
        except sp.TimeoutExpired:
            proc.kill()
            raise

        buffer_text = buffer.getvalue().decode()
        _logger.info(buffer_text)
        self.assertTrue(expected_text in buffer_text,
            f"The subprocess did not write the prelude in under {timeout} seconds.")

    @unittest.skipIf(select_not_available(), SELECT_MESSAGE)
    def test_i18n_export(self):
        expected_text = textwrap.dedent("""\
            # Translation of Odoo Server.
            # This file contains the translation of the following modules:
            # \t* base
        """)
        command_args = ('i18n', 'export', '-d', self.env.cr.dbname, '-o', '-', 'base')
        self._expect(command_args, expected_text)

    @unittest.skipIf(select_not_available(), SELECT_MESSAGE)
    def test_server_http_interface_deprecation(self):
        expected_text = (
            "odoo.tools.config: missing --http-interface/http_interface,"
            " using 0.0.0.0 by default, will change to 127.0.0.1 in 20.0"
        )
        command_args = ('-d', self.env.cr.dbname, '-i', 'base', '-p', '8075')
        config["stop_after_init"] = False
        for map_ in config.options.maps:
            if map_ is config._file_options and 'http_interface' in map_:
                map_['http_interface'] = ''
        self._expect(command_args, expected_text, maxlen=2048, timeout=10, stream=sys.stderr)
