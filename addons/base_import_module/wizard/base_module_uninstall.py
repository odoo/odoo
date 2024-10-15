# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import base


class BaseModuleUninstall(base.BaseModuleUninstall):

    def _modules_to_display(self, modules):
        return super()._modules_to_display(modules) | modules.filtered('imported')
