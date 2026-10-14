# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os
import re
import subprocess
from unittest import skipIf
from odoo import tools
from odoo.tests import tagged
from odoo.tools.misc import file_path
from odoo.modules import get_modules

from .common import LintCase

_logger = logging.getLogger(__name__)

try:
    eslint = tools.misc.find_in_path('eslint')
except IOError:
    eslint = None


@skipIf(eslint is None, "eslint tool not found on this system")
@tagged("test_themes")
class TestESLint(LintCase):

    longMessage = True

    def _test_eslint(self, modules, config_path, options=(), flat_config=False, extensions=('js',)):
        """ Test that there are no eslint errors in the static files of the
        given extensions (javascript files by default) """

        files_to_check = [
            p
            for ext in extensions
            for p in self.iter_module_files(f'**/static/**/*.{ext}', modules=modules)
            if not re.match('.*/libs?/.*', p)  # don't check libraries
            if not re.match('.*/o_spreadsheet/o_spreadsheet.js', p) # don't check generated code
        ]
        _logger.info('Testing %s %s files', len(files_to_check), '/'.join(extensions))
        if not files_to_check:
            # without file arguments, eslint lints the whole cwd
            return
        cwd = None
        if flat_config:
            # flat config ignores, with only a warning, files outside of the base
            # path (the cwd when using -c), so run from the deepest directory
            # containing every file to check
            cwd = os.path.commonpath([os.path.dirname(p) for p in files_to_check])
        cmd = [eslint, '--no-ignore', *options, '-c', config_path] + files_to_check
        process = subprocess.run(cmd, capture_output=True, encoding="utf-8", check=False, cwd=cwd)
        self.assertEqual(process.returncode, 0, msg=f"""
stdout: {process.stdout}
Perhaps you might benefit from installing the tooling found at:
https://github.com/odoo/odoo/wiki/Javascript-coding-guidelines#use-a-linter \n
stderr: {process.stderr}
""")

    def test_eslint(self):
        basic_test, strict_test = [], []
        for module in get_modules():
            strict_test.append(module) if re.search(r'^point_of_sale$|^pos_.*$|^.*_pos$|^.*_pos_.*$|^iot$|^iot_.*$|^obox$|^obox_.*$', module) else basic_test.append(module)

        version = subprocess.run([eslint, '--version'], capture_output=True, encoding="utf-8", check=True).stdout
        major = int(re.match(r'v(\d+)\.', version)[1])
        if major < 8:
            # the legacy configs use the es2022 env, only known since eslint 8
            _logger.warning("eslint@%s is too old, use eslint@8 or later", major)
            return
        if major == 8:
            configs = ['test_lint/tests/eslintrc', 'web/tooling/_eslintrc.json']
            options, flat_config = ['--no-eslintrc'], False
        else:
            # eslintrc support is removed in eslint 10, use flat config from 9 on
            configs = ['test_lint/tests/eslint.config.cjs', 'web/tooling/_eslint.config.cjs']
            options, flat_config = [], True

        for modules, config in zip([basic_test, strict_test], configs):
            with self.subTest(config=config):
                self._test_eslint(modules, file_path(config), options, flat_config)
