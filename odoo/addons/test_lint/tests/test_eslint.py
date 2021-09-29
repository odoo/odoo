# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
import subprocess
from unittest import skipIf
from odoo import tools

from . import lint_case

RULES = ('{'
        '"no-undef": "error",'
        '"no-restricted-globals": ["error", "event", "self"],'
        '"no-const-assign": ["error"],'
        '"no-debugger": ["error"],'
        '"no-dupe-class-members": ["error"]'
        '}'
)
PARSER_OPTIONS = '{ecmaVersion: 2019, sourceType: module}'
GLOBAL = ','.join([
        'owl',
        'odoo',
        '$',
        'jQuery',
        '_',
        'Chart',
        'fuzzy',
        'QWeb2',
        'Popover',
        'StackTrace',
        'QUnit',
        'luxon',
        'moment',
        'py',
        'ClipboardJS',
        'globalThis',
])

_logger = logging.getLogger(__name__)

try:
    eslint = tools.misc.find_in_path('eslint')
except IOError:
    eslint = None

@skipIf(eslint is None, "eslint tool not found on this system")
class TestESLint(lint_case.LintCase):

    longMessage = True

    def test_eslint_version(self):
        """ Test that there are no eslint errors in javascript files """

        files_to_check = [
            p for p in self.iter_module_files('**/static/**/*.js')
            if not re.match('.*/libs?/.*', p)  # don't check libraries
        ]

        _logger.info('Testing %s js files', len(files_to_check))
        # https://eslint.org/docs/user-guide/command-line-interface
        cmd = [eslint, '--no-eslintrc', '--env', 'browser', '--env', 'es2017', '--parser-options', PARSER_OPTIONS, '--rule', RULES, '--global', GLOBAL] + files_to_check
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
        self.assertEqual(process.returncode, 0, msg=process.stdout.decode())
