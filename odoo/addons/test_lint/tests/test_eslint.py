# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
import subprocess
from unittest import skipIf
from odoo import tools
from odoo.tests import tagged
from odoo.tools.misc import file_path
from odoo.modules import get_modules

from . import lint_case

_logger = logging.getLogger(__name__)

try:
    eslint = tools.misc.find_in_path('eslint')
except IOError:
    eslint = None


@skipIf(eslint is None, "eslint tool not found on this system")
@tagged("test_themes")
class TestESLint(lint_case.LintCase):

    longMessage = True

    def _test_eslint(self, modules, eslintrc_path):
        """ Test that there are no eslint errors in javascript files """

        files_to_check = [
            p for p in self.iter_module_files('**/static/**/*.js', modules=modules)
            if not re.match('.*/libs?/.*', p)  # don't check libraries
            if not re.match('.*/o_spreadsheet/o_spreadsheet.js', p) # don't check generated code
        ]
        _logger.info('Testing %s js files', len(files_to_check))
        cmd = [eslint, '--no-ignore', '--no-eslintrc', '-c', eslintrc_path] + files_to_check
        process = subprocess.run(cmd, capture_output=True, encoding="utf-8", check=False)
        self.assertEqual(process.returncode, 0, msg=f"""
stdout: {process.stdout}
Perhaps you might benefit from installing the tooling found at:
https://github.com/odoo/odoo/wiki/Javascript-coding-guidelines#use-a-linter \n
stderr: {process.stderr}
""")

    def test_eslint(self):
        basic_test, strict_test = [], []
        for module in get_modules():
            strict_test.append(module) if re.search('^point_of_sale$|^pos_.*$|^.*_pos$|^.*_pos_.*$', module) else basic_test.append(module)
        self._test_eslint(basic_test, file_path('test_lint/tests/eslintrc'))
        self._test_eslint(strict_test, file_path('web/tooling/_eslintrc.json'))
