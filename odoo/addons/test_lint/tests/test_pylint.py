# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import os
import platform
import sys
from os.path import join

try:
    import pylint
except ImportError:
    pylint = None
import subprocess

from odoo import tools
from odoo.modules import get_modules, get_module_path
from odoo.tests import TransactionCase
from odoo.tools.which import which

HERE = os.path.dirname(os.path.realpath(__file__))

_logger = logging.getLogger(__name__)


class TestPyLint(TransactionCase):
    def _skip_test(self, reason):
        _logger.warning(reason)
        self.skipTest(reason)

    def test_pylint(self):
        if pylint is None:
            self._skip_test('please install pylint')
        required_pylint_version = tools.parse_version('1.7.0')
        pylint_version = getattr(pylint, '__version__', '0.0.1')
        _logger.runbot("pylint version: %s", pylint_version)
        if tools.parse_version(pylint_version) < required_pylint_version:
            self._skip_test('please upgrade pylint to >= %s' % required_pylint_version)

        paths = {tools.config['root_path']}
        for module in get_modules():
            module_path = get_module_path(module)
            if module_path.startswith(join(tools.config['root_path'], 'addons')):
                continue
            paths.add(module_path)

        options = [
            '--rcfile=%s' % os.devnull,
            '--disable=all,useless-option-value',
            '--enable=' + ','.join([
                'used-before-assignment',
                'undefined-variable',
                'eval-used',
                'unreachable',
                'function-redefined',

                # custom checkers
                'sql-injection',
                'gettext-variable',
                'gettext-placeholders',
                'gettext-repr',
                'raise-unlink-override',
            ]),
            '--reports=n',
            "--msg-template='{msg} ({msg_id}) at {path}:{line}'",
            '--load-plugins=' + ','.join([
                "_pylint_path_setup",
                "pylint.extensions.bad_builtin",
                "_odoo_checker_sql_injection",
                "_odoo_checker_gettext",
                "_odoo_checker_unlink_override",
            ]),
            '--bad-functions=input',
            '--deprecated-modules=' + ','.join([
                'csv',
                'urllib',
                'cgi',
                *tools.constants.SUPPORTED_DEBUGGER,
            ]),
        ]

        stdlib_prefixes = tuple({sys.prefix, sys.base_prefix, sys.exec_prefix, sys.base_exec_prefix})
        pypath = os.pathsep.join([HERE, *(p for p in sys.path if not p.startswith(stdlib_prefixes))])
        env = {
            **os.environ,
            "PYTHONPATH": pypath,
            "ADDONS_PATH": os.pathsep.join(tools.config['addons_path']),
        }

        if os.name == 'posix' and platform.system() != 'Darwin':
            # Pylint started failing at ~2.4g from time to time.
            # Removing the memory limit will solve this issue for a while (runbot limit is arroung 5g)
            def preexec():
                import resource
                resource.setrlimit(resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        else:
            preexec = None

        try:
            r = subprocess.run(
                [which('pylint'), *options, *paths],
                capture_output=True, text=True, env=env,
                preexec_fn=preexec,
            )
        except (OSError, IOError):
            self._skip_test('pylint executable not found in the path')
        else:
            if r.returncode:
                self.fail(f"pylint test failed:\n\n{r.stdout}\n{r.stderr}".strip())
            else:
                _logger.debug("%s", r.stdout)
