# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
import subprocess
from unittest import skipIf
from odoo import tools
from odoo.modules.module import get_resource_path
from odoo.tests import tagged

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

    def test_eslint(self):
        """ Test that there are no eslint errors in javascript files """

        files_to_check = [
            p for p in self.iter_module_files('**/static/**/*.js')
            if not re.match('.*/libs?/.*', p)  # don't check libraries
            if not re.match('.*/o_spreadsheet/o_spreadsheet.js', p) # don't check generated code
        ]
        eslintrc_path = get_resource_path('test_lint', 'tests', 'eslintrc')

        _logger.info('Testing %s js files', len(files_to_check))
        # https://eslint.org/docs/user-guide/command-line-interface
        cmd = [eslint, '--no-eslintrc', '-c', eslintrc_path] + files_to_check
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(process.returncode, 0, msg=process.stdout.decode())
