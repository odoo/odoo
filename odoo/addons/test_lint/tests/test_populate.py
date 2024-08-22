# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo.tools.misc import file_open
from . import lint_case

_logger = logging.getLogger(__name__)

class TestPopulate(lint_case.LintCase):

    def test_populate(self):
        for python_file in self.iter_module_files('**/*.py'):
            if python_file == __file__:
                continue
            with file_open(python_file) as f:
                content = f.read()
                if 'def _populate' in content and ('import random' in content or 'from random' in content):
                    _logger.error('Using non seeded random in populate is forbidden in %s', python_file)
