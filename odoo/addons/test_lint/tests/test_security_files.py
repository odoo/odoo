import logging
import re

from odoo import tools

from . import lint_case

_logger = logging.getLogger(__name__)


class TestSecurityFiles(lint_case.LintCase):

    def test_access_to_public_user(self):
        """
        Instead of granting access to the public group, use everyone for consistency.
        """
        error_count = 0
        re_public = re.compile(r'group_public\b')
        for file_path in self.iter_module_files("**/ir.access.csv"):
            if '/test_orm/' in file_path:
                # skip for access_test_orm_model_some_access
                continue
            with tools.file_open(file_path, "r") as f:
                file_content = f.read()
                if m := re_public.search(file_content):
                    lineno = file_content[: m.start()].count("\n") + 1
                    _logger.error(
                        """The file %s:%d contains group_public, use group_everyone instead.""",
                        file_path,
                        lineno,
                    )
                    error_count += 1
        self.assertEqual(error_count, 0)
