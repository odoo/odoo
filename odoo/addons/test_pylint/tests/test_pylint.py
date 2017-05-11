# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
try:
    import pylint
except ImportError:
    pylint = None
import subprocess
from distutils.version import LooseVersion
from os import devnull
from os.path import join

from odoo.tests.common import TransactionCase
from odoo import tools
from odoo.modules import get_modules, get_module_path


_logger = logging.getLogger(__name__)


class TestPyLint(TransactionCase):

    ENABLED_CODES = [
        'E0601',  # using variable before assignment
        'W0123',  # eval used
        'W0101',  # unreachable code

        'misplaced-future',
        'relative-import',
        'deprecated-module',
        'import-star-module-level',

        'bad-builtin',

        'dict-iter-method',
        'dict-view-method',

        'long-suffix',

        'metaclass-assignment',
    ]

    BAD_FUNCTIONS = [
        'apply',
        'cmp',
        'coerce',
        'execfile',
        'input',
        'intern',
        'long',
        'raw_input',
        'reload',
        'xrange',
        'long',
        'map',
        'filter',
        'zip',
        # TODO: enable once report has been removed
        # 'file',
        # 'reduce',
    ]

    def _skip_test(self, reason):
        _logger.warn(reason)
        self.skipTest(reason)

    def test_pylint(self):
        if pylint is None:
            self._skip_test('please install pylint')
        if LooseVersion(getattr(pylint, '__version__', '0.0.1')) < LooseVersion('1.6.4'):
            self._skip_test('please upgrade pylint to >= 1.6.4')

        paths = [tools.config['root_path']]
        for module in get_modules():
            module_path = get_module_path(module)
            if not module_path.startswith(join(tools.config['root_path'], 'addons')):
                paths.append(module_path)

        options = [
            '--disable=all',
            '--enable=%s' % ','.join(self.ENABLED_CODES),
            '--reports=n',
            "--msg-template='{msg} ({msg_id}) at {path}:{line}'",
            '--load-plugins=pylint.extensions.bad_builtin',
            '--bad-functions=%s' % ','.join(self.BAD_FUNCTIONS),
        ]

        try:
            with open(devnull, 'w') as devnull_file:
                process = subprocess.Popen(['pylint'] + options + paths, stdout=subprocess.PIPE, stderr=devnull_file)
        except (OSError, IOError):
            self._skip_test('pylint executable not found in the path')
        else:
            out = process.communicate()[0]
            if process.returncode:
                self.fail("\n" + out)
