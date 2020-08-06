#!/usr/bin/env python
# -*- coding: utf-8 -*-
import glob
import os
import logging
import warnings
import sys

import odoo
import odoo.cli.server
from odoo.modules.module import get_module_root


_logger = logging.getLogger(__name__)


def main():
    path = odoo.config['startsc_path']

    # Set a default db_name and dbfilter if the path point a module and
    # the addons_path is updated to include it. If the path instead
    # point an addons path, only the addons_path is updated. Fail if the
    # path is not relevant.

    if module_root := get_module_root(path):
        module_name = os.path.basename(module_root)
        odoo.config.setdefault('db_name', module_name)
        odoo.config.setdefault('dbfilter', f'^{module_name}$')
        odoo.config['addons_path'] += (os.path.dirname(module_root),)
    elif glob.glob(os.path.join(path, '*/__manifest__.py')):
        odoo.config['addons_path'] += (path,)
    elif glob.glob(os.path.join(path, '*/__openerp__.py')):
        warnings.warn(
            'Using "__openerp__.py" as module manifest is deprecated, '
            'please rename the file to "__manifest__.py"', DeprecationWarning)
        odoo.config['addons_path'] += (path,)
    else:
        _logger.critical("Not a valid project directory: %s", path)
        sys.exit(1)

    odoo.cli.server.main()
