# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os

from odoo import api, fields, models
_logger = logging.getLogger(__name__)


class IrModuleModule(models.Model):
    _name = "ir.module.module"
    _inherit = _name

    image_ids = fields.One2many('ir.attachment', 'res_id',
                                domain=[('res_model', '=', _name), ('mimetype', '=like', 'image/%')],
                                string='Screenshots', readonly=True)
    # for kanban view
    is_installed_on_current_website = fields.Boolean(compute='_compute_is_installed_on_current_website')

    @api.multi
    def _compute_is_installed_on_current_website(self):
        for module in self:
            module.is_installed_on_current_website = module == self.env['website'].get_current_website().theme_id

    @api.multi
    def write(self, vals):
        if vals.get('state') == 'installed' and self.name.startswith('theme_'):
            _logger.info('Module %s has been loaded as theme template' % self.name)
        return super(IrModuleModule, self).write(vals)

    @api.multi
    def _get_module_data(self, model_name):
        IrModelData = self.env['ir.model.data']
        records = self.env[model_name]

        for module in self:
            imd_ids = IrModelData.search([('module', '=', module.name), ('model', '=', model_name)]).mapped('res_id')
            records |= self.env[model_name].browse(imd_ids)
        return records

    @api.multi
    def _load_one_theme_module(self, website, loaded):
        # loaded is a dict updated in place !
        # keep previous record created to update overrided record
        _logger.info('Load theme %s for website %s from template.' % (self.mapped('name'), website.id))

        for attach in self._get_module_data('theme.ir.attachment'):
            already_create = loaded['attachments'].filtered(lambda x: x.key == attach.key)
            new_attach = {
                'public': True,
                'res_model': 'ir.ui.view',
                'type': 'url',
                'name': attach.name,
                'url': attach.url,
                'website_id': website.id,
                'theme_template_id': attach.id,
            }
            if already_create:
                already_create.update(new_attach)
            else:  # if module B override attachment from dependence A
                loaded['attachments'] += self.env['ir.attachment'].create(new_attach)

        for view in self._get_module_data('theme.ir.ui.view'):
            if view.inherit_id and view.inherit_id._name == 'theme.ir.ui.view':
                view.inherit_id = loaded['views'].filtered(lambda x: x.theme_template_id == view.inherit_id)

            new_view = {
                'type': view.type or 'qweb',
                'name': view.name,
                'arch': view.arch,
                'key': view.key,
                'arch_fs': view.arch_fs,
                'priority': view.priority,
                'active': view.active,
                'inherit_id': view.inherit_id and view.inherit_id.id,
                'theme_template_id': view.id,
                'website_id': website.id,
            }
            if view.mode:  # if not provided, computed automatically (if inherit_id or not)
                new_view['mode'] = view.mode
            loaded['views'] += self.env['ir.ui.view'].create(new_view)

        for page in self._get_module_data('theme.website.page'):
            new_page = {
                'url': page.url,
                'view_id': loaded['views'].filtered(lambda x: x.theme_template_id == page.view_id).id,
                'website_indexed': page.website_indexed,
                'theme_template_id': page.id,
            }
            loaded['pages'] += self.env['website.page'].create(new_page)

        for menu in self._get_module_data('theme.website.menu'):
            new_menu = {
                'name': menu.name,
                'url': menu.url,
                'page_id': loaded['pages'].filtered(lambda x: x.theme_template_id == menu.page_id).id,
                'new_window': menu.new_window,
                'sequence': menu.sequence,
                'parent_id': loaded['menus'].filtered(lambda x: x.theme_template_id == menu.parent_id).id,
                'theme_template_id': menu.id,
            }
            loaded['menus'] += self.env['website.menu'].create(new_menu)

        return True

    @api.multi
    def _unload_one_theme_module(self, website):
        _logger.info('Unload theme %s for website %s from template.' % (self.mapped('name'), website.id))

        for module in self:
            menus = module._get_module_data('theme.website.menu')
            menu_todel = menus.mapped('copy_ids').filtered(lambda m: m.website_id == website)
            menu_todel.unlink()

            pages = module._get_module_data('theme.website.page')
            pages_todel = pages.mapped('copy_ids').filtered(lambda p: p.website_id == website)
            pages_todel.unlink()

            attachs = module._get_module_data('theme.ir.attachment')
            atachs_todel = attachs.mapped('copy_ids').filtered(lambda a: a.website_id == website)
            atachs_todel.unlink()

            views = module._get_module_data('theme.ir.ui.view')
            views_todel = views.mapped('copy_ids').filtered(lambda v: v.website_id == website)
            views_todel.unlink()

    def _remove_theme_on_website(self, website):
        installed_deps = self + website.theme_id.upstream_dependencies(exclude_states=('',)).filtered(lambda x: x.name.startswith('theme_'))
        for mod in installed_deps:
            mod._unload_one_theme_module(website)

    def _copy_theme_on_website(self, website):
        loaded = {
            'views': self.env['ir.ui.view'],
            'attachments': self.env['ir.attachment'],
            'pages': self.env['website.page'],
            'menus': self.env['website.menu'],
        }
        mods_to_load = reversed(self + self.upstream_dependencies(exclude_states=('',)).filtered(lambda x: x.name.startswith('theme_')))
        for mod in mods_to_load:
            mod._load_one_theme_module(website, loaded)
            self.env['theme.utils']._post_copy(mod)

    @api.multi
    def button_choose_theme(self):
        website = self.env['website'].get_current_website()

        # Unload previous theme
        if website.theme_id:
            website.theme_id._remove_theme_on_website(website)

        website.theme_id = self

        # create template data of missing theme
        next_action = False
        if self.state != 'installed':
            next_action = self.button_immediate_install()

        # Copy new theme from template table to real table
        self._copy_theme_on_website(website)

        # Alter next action for redirect
        if not next_action:
            next_action = website.button_go_website()
        if next_action.get('tag') == 'reload' and not next_action.get('params', {}).get('menu_id'):
            next_action = self.env.ref('website.action_website').read()[0]

        return next_action

    def button_remove_theme(self):
        website = self.env['website'].get_current_website()
        self._remove_theme_on_website(website)
        website.theme_id = False

    def button_refresh_theme(self):
        website = self.env['website'].get_current_website()
        # load data from xml to template table
        self.button_immediate_upgrade()

        # delete current theme
        # todo: quid of no_update record?
        self.button_remove_theme()

        # copy data from template table to real table
        self._copy_theme_on_website(website)

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
