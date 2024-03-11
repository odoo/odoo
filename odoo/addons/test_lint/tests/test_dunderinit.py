# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from pathlib import Path

from odoo.modules import get_modules, get_module_path
from . import lint_case

_logger = logging.getLogger(__name__)

# whitelist that allow data modules only
WHITELIST = ['test_data_module', ]

class TestDunderinit(lint_case.LintCase):

    def test_dunderinit(self):
        """ Test that __init__.py exists in Odoo modules, otherwise they won't get packaged"""

        modules_list = [mod for mod in get_modules() if mod not in WHITELIST]
        for mod in modules_list:
            dunderinit_path = Path(get_module_path(mod)) / '__init__.py'
            self.assertTrue(dunderinit_path.is_file(), "Missing `__init__.py ` in module %s" % mod)

        _logger.info('%s modules checked', len(modules_list))
