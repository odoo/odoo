# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from pathlib import Path

from odoo.modules import get_modules, get_module_path
from . import lint_case
import re
_logger = logging.getLogger(__name__)

import_orm_re = re.compile(r'^(from|import)\s+odoo\.orm')


class TestDunderinit(lint_case.LintCase):

    def test_addons_orm_import(self):
        """ Test that odoo.orm is not imported in Odoo modules"""

        for module in get_modules():
            module_path = Path(get_module_path(module))
            for path in module_path.rglob("**/*.py"):
                for line in path.read_text().splitlines():
                    if import_orm_re.match(line):
                        self.fail(f"Do not import directly from odoo.orm, use odoo.(api,fields,models): {path}")
