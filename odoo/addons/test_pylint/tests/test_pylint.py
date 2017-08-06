# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
try:
    import pylint
    from pylint import lint
    from pylint.reporters import BaseReporter
except ImportError:
    pylint = None
from distutils.version import LooseVersion
from os.path import join

from odoo.tests.common import TransactionCase
from odoo import tools
from odoo.modules import get_modules, get_module_path


_logger = logging.getLogger(__name__)


class Reporter(BaseReporter):
    messages = []

    def handle_message(self, msg):
        self.messages.append(msg)


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
        'old-ne-operator',
        'old-octal-operator',
        'parameter-unpacking',

        'metaclass-assignment',
        'deprecated-module',

        'exception-message-attribute',
        'indexing-exception',
        'old-raise-syntax',
        'raising-string',
        'unpacking-in-except',
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

        'file',
        'reduce',
    ]

    BAD_MODULES = [
        'commands',
        'cPickle',
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
        'UserDict',
        'UserString',
        'UserList',
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
            '--deprecated-modules=%s' % ','.join(self.BAD_MODULES)
        ]

        res = lint.Run(options + paths, reporter=Reporter(), exit=False)
        msgs = res.linter.reporter.messages
        out = ""
        for msg in msgs:
            out += msg.format(res.linter.config.msg_template) + '\n'
        if msgs:
            self.fail("Pylint %d errors found: \n%s" % (len(msgs), out))
