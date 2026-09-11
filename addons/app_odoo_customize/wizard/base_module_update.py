# -*- coding: utf-8 -*-

import os
import lxml.html
import odoo
import logging
from odoo import api, fields, models, addons, modules, tools, Command
from odoo.modules.module import get_module_path

_logger = logging.getLogger(__name__)

STANDARD_MODULES = ['web', 'web_enterprise', 'theme_common', 'base']


class BaseModuleUpdate(models.TransientModel):
    _inherit = "base.module.update"

    def update_addons_paths(self):
        addons_path_obj = self.env['ir.module.addons.path']
        ad_paths = addons.__path__
        path_sep = os.path.sep
        for path in ad_paths:
            if not addons_path_obj.search([('path', '=', path)]):
                path_temp = path

                if len(path_temp) > 42:
                    path_temp = '%s......%s' % (path[:12], path[-19:])

                addons_path_obj.sudo().create({
                    'name': path.split(path_sep)[-1],
                    'path': path,
                    'path_temp': path_temp,
                })

        for addons_path_id in addons_path_obj.search([]):
            if addons_path_id.path not in ad_paths:
                addons_path_id.unlink()

    def update_module_addons_paths(self):
        addons_path_obj = self.env['ir.module.addons.path']
        path_sep = os.path.sep
        for module_id in self.env['ir.module.module'].search([]):
            module_path = get_module_path(module_id.name)
            if not module_path:
                continue
            addons_path = module_path.rstrip(module_id.name).rstrip(path_sep)
            addons_path_id = addons_path_obj.search([('path', '=', addons_path)])

            if addons_path_id:
                module_id.addons_path_id = addons_path_id.id

    def update_module(self):
        res = super(BaseModuleUpdate, self).update_module()
        self.update_addons_paths()
        self.update_module_addons_paths()
        return res
