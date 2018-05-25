# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
try:
    import pylint
except ImportError:
    pylint = None
import subprocess
from distutils.version import LooseVersion
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
        'E0601',  # using variable before assignment
        'W0123',  # eval used
        'W0101',  # unreachable code

        'mixed-indentation',

        # py3k checks
        'print-statement',
        'backtick',
        'next-method-called',

        'misplaced-future',
        'relative-import',
        'deprecated-module',
        'import-star-module-level',

        'bad-builtin',

        'dict-iter-method',
        'dict-view-method',

        'long-suffix',
        'old-ne-operator',
        'old-octal-operator',
        'parameter-unpacking',
        'invalid-string-codec',

        'metaclass-assignment',
        'deprecated-module',

        'exception-message-attribute',
        'indexing-exception',
        'old-raise-syntax',
        'raising-string',
        'unpacking-in-except',

        'no-comma-exception',
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

        'basestring',
        'unichr',
        'unicode',

        'file',
        'reduce',
    ]

    BAD_MODULES = [
        'commands',
        'cPickle',
        'csv',
        'cStringIO',
        'md5',
        'urllib',
        'urllib2',
        'urlparse',
        'sgmllib',
        'sha',
        'cgi',
        'htmlentitydefs',
        'HTMLParser',
        'Queue',
        'StringIO',
        'UserDict',
        'UserString',
        'UserList',
    ] + list(tools.SUPPORTED_DEBUGGER)

    def _skip_test(self, reason):
        _logger.warn(reason)
        self.skipTest(reason)

    def test_pylint(self):
        if pylint is None:
            self._skip_test('please install pylint')
        required_pylint_version = LooseVersion('1.6.4')
        if sys.version_info >= (3, 6):
            required_pylint_version = LooseVersion('1.7.0')
        if LooseVersion(getattr(pylint, '__version__', '0.0.1')) < required_pylint_version:
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
            '--load-plugins=pylint.extensions.bad_builtin,_odoo_checkers',
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
