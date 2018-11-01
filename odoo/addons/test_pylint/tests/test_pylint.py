# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import inspect
import logging
try:
    import pylint
    from pylint import lint
    from pylint.reporters import CollectingReporter
except ImportError:
    pylint = None
from distutils.version import LooseVersion
import os
from os.path import join
import sys

from odoo.tests.common import TransactionCase
from odoo import tools
from odoo.modules import get_modules, get_module_path

_logger = logging.getLogger(__name__)


class TestPyLint(TransactionCase):

    ENABLED_CODES = [
        'used-before-assignment',
        'undefined-variable',
        'eval-used',
        'unreachable',

        'mixed-indentation',

        # odoo checks
        'sql-injection',

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
        pylint_version = getattr(pylint, '__version__', '0.0.1')
        _logger.info("pylint version used: %s", pylint_version)

        import astroid
        astroid_version = getattr(astroid.__pkginfo__, 'version', '0.0.1')
        _logger.info("astroid version used: %s", astroid_version)

        import subprocess
        pylint_bin = tools.which('pylint')
        process = subprocess.Popen([pylint_bin] + ["--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,)
        out, err = process.communicate()
        _logger.info("pylint_bin version used: %s", out)

        import os
        _logger.info("Current working directory: %s", os.getcwd())
        _logger.info("List dirs: %s", os.listdir(os.getcwd()))

        if LooseVersion(pylint_version) < required_pylint_version:
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
            '--load-plugins=pylint.extensions.bad_builtin,odoo.addons.test_pylint.tests._odoo_checkers',
            '--bad-functions=%s' % ','.join(self.BAD_FUNCTIONS),
            '--deprecated-modules=%s' % ','.join(self.BAD_MODULES),
            '--score=n',
        ]

        run_args = inspect.getargspec(lint.Run.__init__).args
        # pylint dual compatibility
        do_exit_kwarg = {'exit': False} if 'exit' in run_args else {'do_exit': False}
        res = lint.Run(options + paths, reporter=CollectingReporter(), **do_exit_kwarg)
        msgs = res.linter.reporter.messages
        msg = '\n'.join([msg.format(res.linter.config.msg_template) for msg in msgs])
        if msg:
            self.fail("Pylint errors: %d\n%s" % (len(msgs), msg))
