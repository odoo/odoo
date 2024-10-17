# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import controllers
from . import models
from . import wizard

from .models.base_import_module import BaseImportModule
from .models.ir_module import IrModuleModule
from .models.ir_ui_view import IrUiView
from .wizard.base_module_uninstall import BaseModuleUninstall
