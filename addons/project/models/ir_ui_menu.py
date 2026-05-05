# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        if not self.env.user.has_group('project.group_project_manager') and (menu := self.env.ref('project.rating_rating_menu_project', raise_if_not_found=False)):
            res.append(menu.id)
        if self.env.user.has_group('project.group_project_stages'):
            for xmlid in [
                'project.menu_projects',
                'project.menu_projects_config',
            ]:
                if menu := self.env.ref(xmlid, raise_if_not_found=False):
                    res.append(menu.id)
        if not (
            self.env.user.has_group('project.group_project_stages') and
            self.env.user.has_group('base.group_no_one')
            ) and menu := self.env.ref('project.menu_project_config_project_stage', raise_if_not_found=False):
            res.append(menu.id)

        return res
