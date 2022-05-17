# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
try:
    import pylint
except ImportError:
    pylint = None
import subprocess
import os
from os.path import join
import sys

from odoo.tests.common import TransactionCase
from odoo import tools
from odoo.modules import get_modules, get_module_path

HERE = os.path.dirname(os.path.realpath(__file__))

_logger = logging.getLogger(__name__)


class TestPyLint(TransactionCase):

    ENABLED_CODES = [
        'used-before-assignment',
        'undefined-variable',
        'eval-used',
        'unreachable',
        'function-redefined',

        # custom checkers
        'sql-injection',
        'gettext-variable',
        'raise-unlink-override',
    ]

    BAD_FUNCTIONS = [
        'input',
    ]

    BAD_MODULES = [
        'csv',
        'urllib',
        'cgi',
    ] + list(tools.SUPPORTED_DEBUGGER)

    def _skip_test(self, reason):
        _logger.warning(reason)
        self.skipTest(reason)

    def test_pylint(self):
        if pylint is None:
            self._skip_test('please install pylint')
        required_pylint_version = tools.parse_version('1.6.4')
        if sys.version_info >= (3, 6):
            required_pylint_version = tools.parse_version('1.7.0')
        if tools.parse_version(getattr(pylint, '__version__', '0.0.1')) < required_pylint_version:
            self._skip_test('please upgrade pylint to >= %s' % required_pylint_version)

        paths = [tools.config['root_path']]
        for module in get_modules():
            module_path = get_module_path(module)
            if not module_path.startswith(join(tools.config['root_path'], 'addons')):
                paths.append(module_path)

        options = [
            '--rcfile=%s' % os.devnull,
            '--disable=all',
            '--enable=%s' % ','.join(self.ENABLED_CODES),
            '--reports=n',
            "--msg-template='{msg} ({msg_id}) at {path}:{line}'",
            '--load-plugins=pylint.extensions.bad_builtin,_odoo_checker_sql_injection,_odoo_checker_gettext,_odoo_checker_unlink_override',
            '--bad-functions=%s' % ','.join(self.BAD_FUNCTIONS),
            '--deprecated-modules=%s' % ','.join(self.BAD_MODULES)
        ]

        pypath = HERE + os.pathsep + os.environ.get('PYTHONPATH', '')
        env = dict(os.environ, PYTHONPATH=pypath)
        try:
            pylint_bin = tools.which('pylint')
            process = subprocess.Popen(
                [pylint_bin] + options + paths,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
        except (OSError, IOError):
            self._skip_test('pylint executable not found in the path')
        else:
            out, err = process.communicate()
            if process.returncode:
                self.fail("pylint test failed:\n" + (b"\n" + out + b"\n" + err).decode('utf-8').strip())
