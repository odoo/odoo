# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        if not self.env.user.has_group('project.group_project_manager'):
            rating = self.env.ref('project.rating_rating_menu_project', raise_if_not_found=False)
            if rating:
                res.append(rating.id)
        if self.env.user.has_group('project.group_project_stages'):
            res.append(self.env.ref('project.menu_projects').id)
            res.append(self.env.ref('project.menu_projects_config').id)
        return res
