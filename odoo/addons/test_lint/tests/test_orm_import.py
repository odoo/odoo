# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo.tools import file_open

from .common import LintCase

import_orm_re = re.compile(r'^(from|import)\s+odoo\.orm', flags=re.MULTILINE)


class TestNoOrmImport(LintCase):

    def test_addons_orm_import(self):
        """ Test that odoo.orm is not imported in Odoo modules"""

        for path in self.iter_module_files('*.py'):
            with file_open(path, 'r') as f:
                if import_orm_re.search(f.read()):
                    self.fail(f"Do not import directly from odoo.orm, use odoo.(api,fields,models): {path}")
