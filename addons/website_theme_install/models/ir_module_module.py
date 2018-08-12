# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class IrModuleModule(models.Model):
    _name = "ir.module.module"
    _inherit = _name

    image_ids = fields.One2many('ir.attachment', 'res_id',
                                domain=[('res_model', '=', _name), ('mimetype', '=like', 'image/%')],
                                string='Screenshots', readonly=True)
    is_installed_on_current_website = fields.Boolean(compute='_compute_is_installed_on_current_website')

    @api.multi
    def _compute_is_installed_on_current_website(self):
        for module in self:
            module.is_installed_on_current_website = module == self.env['website'].get_current_website().installed_theme_id

    @api.multi
    def write(self, vals):
        if vals.get('state') == 'installed':
            self._handle_auto_installs()

        return super(IrModuleModule, self).write(vals)

    @api.multi
    def _assign_views(self):
        IrModelData = self.env['ir.model.data']
        for module in self:
            views = self.env['ir.ui.view'].browse(IrModelData.search([('module', '=', module.name),
                                                                      ('model', '=', 'ir.ui.view')]).mapped('res_id'))
            views.write({
                'theme_id': module.id
            })

    @api.model
    def _handle_auto_installs(self):
        for module in self.search([('auto_install', '=', True), ('name', '=like', 'theme%'), ('state', 'in', ('installed', 'to install'))]):
            theme_deps = module.get_upstream_theme_dependencies()
            websites = self.env['website'].search([]).filtered(lambda w: len(theme_deps - w.theme_ids) == 0)
            if websites:
                _logger.info('auto-loading %s on %s', module.name, websites.mapped('name'))
                websites.write({'theme_ids': [(4, module.id, 0)]})
                module._assign_views()

                # put demo date on first website
                module._make_demo_data_website_specific(websites[0])

    @api.multi
    def _get_module_data(self, model_name):
        IrModelData = self.env['ir.model.data']
        records = self.env[model_name]

        for module in self:
            records |= self.env[model_name].browse(IrModelData.search([('module', '=', module.name), ('model', '=', model_name)]).mapped('res_id'))

        return records

    @api.multi
    def _make_demo_data_website_specific(self, website):
        for module in self:
            menus = module._get_module_data('website.menu')
            menus.with_context(no_cow=True).write({'website_id': website.id})

            pages = module._get_module_data('website.page')
            pages.with_context(no_cow=True).write({'website_id': website.id})
            pages.with_context(no_cow=True).mapped('view_id').write({'website_id': website.id})

    @api.multi
    def _remove_website_specific_demo_data(self, website):
        for module in self:
            menus = module._get_module_data('website.menu')
            menus.filtered(lambda menu: menu.website_id == website).unlink()

            pages = module._get_module_data('website.page')
            pages.filtered(lambda page: page.website_id == website).unlink()

    @api.model
    def update_list(self):
        res = super(IrModuleModule, self).update_list()

        IrAttachment = self.env['ir.attachment']
        existing_urls = IrAttachment.search_read([['res_model', '=', self._name], ['type', '=', 'url']], ['url'])
        existing_urls = [url_wrapped['url'] for url_wrapped in existing_urls]

        for app in self.search([]):
            terp = self.get_module_info(app.name)
            images = terp.get('images', [])
            for image in images:
                image_path = os.path.join(app.name, image)
                if image_path not in existing_urls:
                    image_name = os.path.basename(image_path)
                    IrAttachment.create({
                        'type': 'url',
                        'name': image_name,
                        'datas_fname': image_name,
                        'url': image_path,
                        'res_model': self._name,
                        'res_id': app.id,
                    })

        return res

    def get_upstream_theme_dependencies(self):
        upstream_deps = self.upstream_dependencies(exclude_states=('uninstallable', 'to remove'))
        upstream_theme_deps = upstream_deps.filtered(lambda mod: any(mod.name.startswith(keyword) for keyword in ('theme_', 'snippet_', 'website_animate')))
        return upstream_theme_deps

    @api.multi
    def button_choose_theme(self):
        theme_category = self.env.ref('base.module_category_theme', False)
        theme_hidden_category = self.env.ref('base.module_category_theme_hidden', False)

        theme_category_id = theme_category.id if theme_category else 0
        hidden_categories_ids = [theme_hidden_category.id if theme_hidden_category else 0]
        current_website = self.env['website'].get_current_website()

        themes_to_uninstall = self.search([ # Uninstall the theme(s) which is (are) installed
            ('state', '=', 'installed'),
            ('category_id', 'not in', hidden_categories_ids),
            ('id', 'in', current_website.theme_ids.ids),
            '|', ('category_id', '=', theme_category_id), ('category_id.parent_id', '=', theme_category_id)
        ])

        if themes_to_uninstall:
            themes_to_uninstall.button_immediate_uninstall()

        modules_belonging_to_theme = self + self.get_upstream_theme_dependencies()
        current_website.installed_theme_id = self
        current_website.theme_ids |= modules_belonging_to_theme

        next_action = self.button_immediate_install() # Then install the new chosen one
        modules_belonging_to_theme._assign_views()
        modules_belonging_to_theme._make_demo_data_website_specific(current_website)
        self._handle_auto_installs()
        _logger.info('installed themes %s on %s', modules_belonging_to_theme.mapped('name'), current_website.name)

        if next_action.get('tag') == 'reload' and not next_action.get('params', {}).get('menu_id'):
            next_action = self.env.ref('website.action_website').read()[0]

        return next_action

    @api.multi
    def button_uninstall(self):
        if not any(mod.name.startswith('theme_') for mod in self):
            return super(IrModuleModule, self).button_uninstall()

        # only one theme can be uninstalled
        self.ensure_one()

        Website = self.env['website']
        current_website = Website.get_current_website()
        if Website.search_count([('theme_ids', 'in', self.id)]) > 1:
            modules_belonging_to_theme = self + self.get_upstream_theme_dependencies() + self.downstream_dependencies()
            current_website.installed_theme_id -= modules_belonging_to_theme
            current_website.theme_ids -= modules_belonging_to_theme
            modules_belonging_to_theme._remove_website_specific_demo_data(current_website)
            _logger.info('removed themes %s from %s', modules_belonging_to_theme.mapped('name'), current_website.name)
            return True
        else:
            uninstalled_modules = self + self.downstream_dependencies()
            res = super(IrModuleModule, self).button_uninstall()

            for website in Website.search([]):
                website.installed_theme_id -= uninstalled_modules
                website.theme_ids -= uninstalled_modules
                _logger.info('removed themes %s from %s', uninstalled_modules.mapped('name'), website.name)

            # Attempt to uninstall upstream dependencies. This is
            # necessary for uninstalling e.g. theme_zap, when doing so
            # theme_treehouse should also be removed from the current
            # website. This way the user can install a completely new
            # theme.
            #
            # Make sure to only uninstall every module once with
            # context. Otherwise it might get removed from the current
            # website the first time and the second time it might end
            # up being wrongly uninstalled.
            if self._context.get('uninstall_upstream') is not False:
                for upstream_dependency in self.get_upstream_theme_dependencies().filtered(lambda mod: mod.name.startswith('theme_')):
                    upstream_dependency.with_context(uninstall_upstream=False).button_uninstall()

            return res
