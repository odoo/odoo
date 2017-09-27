# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    @api.multi
    def button_choose_theme(self):
        super(IrModuleModule, self).button_choose_theme()
        next_action = self.env.ref('website_sale.action_open_website').read()[0]
        return next_action

    @api.multi
    def check_theme_installed(self):
        theme_category = self.env.ref('base.module_category_theme', False)
        hidden_category = self.env.ref('base.module_category_hidden', False)
        theme_hidden_category = self.env.ref('base.module_category_theme_hidden', False)

        theme_category_id = theme_category.id if theme_category else 0
        hidden_categories_ids = [hidden_category.id if hidden_category else 0, theme_hidden_category.id if theme_hidden_category else 0]

        res = self.search([
            ('state', '=', 'installed'),
            '|', ('category_id', 'not in', hidden_categories_ids), ('name', '=', 'theme_default'),
            '|', ('category_id', '=', theme_category_id), ('category_id.parent_id', '=', theme_category_id)
        ])
        if res:
            return True
        return False

    def open_shop(self):
        if (self.check_theme_installed()):
            url = '/web?reload#action=website_sale.action_open_website'
            return url
        self.update_list()
        url = '/web?reload#action=website_theme_install.theme_install_kanban_action'
        return url
