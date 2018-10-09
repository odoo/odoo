# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os

from odoo import api, fields, models
_logger = logging.getLogger(__name__)


class IrModuleModule(models.Model):
    _name = "ir.module.module"
    _description = 'Module'
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
        if self and vals.get('state') == 'installed' and self.name.startswith('theme_'):
            _logger.info('Module %s has been loaded as theme template' % self.name)
        return super(IrModuleModule, self).write(vals)

    @api.multi
    def _get_module_data(self, model_name):
        IrModelData = self.env['ir.model.data']
        records = self.env[model_name]

        for module in self:
            imd_ids = IrModelData.search([('module', '=', module.name), ('model', '=', model_name)]).mapped('res_id')
            records |= self.env[model_name].with_context(active_test=False).browse(imd_ids)
        return records

    def _convert_attachment(self, attach, website, **kw):
        new_attach = {
            'key': attach.key,
            'public': True,
            'res_model': 'ir.ui.view',
            'type': 'url',
            'name': attach.name,
            'url': attach.url,
            'website_id': website.id,
            'theme_template_id': attach.id,
        }
        return new_attach

    def _convert_view(self, view, website, **kw):
        inherit = view.inherit_id
        if view.inherit_id and view.inherit_id._name == 'theme.ir.ui.view':
                inherit = view.inherit_id.copy_ids.filtered(lambda x: x.website_id == website)
                if not inherit:
                    # inherit_id not yet created, add to the queue
                    return False
        new_view = {
            'type': view.type or 'qweb',
            'name': view.name,
            'arch': view.arch,
            'key': view.key,
            'inherit_id': inherit and inherit.id,
            'arch_fs': view.arch_fs,
            'priority': view.priority,
            'active': view.active,
            'theme_template_id': view.id,
            'website_id': website.id,
        }

        if view.mode:  # if not provided, it will be computed automatically (if inherit_id or not)
            new_view['mode'] = view.mode

        return new_view

    def _convert_page(self, page, website, **kw):
        new_page = {
            'url': page.url,
            'view_id': page.view_id.copy_ids.filtered(lambda x: x.website_id == website),
            'website_indexed': page.website_indexed,
            'theme_template_id': page.id,
        }
        return new_page

    def _convert_menu(self, menu, website, **kw):
        page_id = menu.page_id.copy_ids.filtered(lambda x: x.website_id == website)
        parent_id = menu.copy_ids.filtered(lambda x: x.website_id == website)
        new_menu = {
            'name': menu.name,
            'url': menu.url,
            'page_id': page_id,
            'new_window': menu.new_window,
            'sequence': menu.sequence,
            'parent_id': parent_id,
            'theme_template_id': menu.id,
        }
        return new_menu

    def _convert(self, model):
        if model == 'ir.ui.view':
            return self._convert_view
        elif model == 'ir.attachment':
            return self._convert_attachment
        elif model == 'website.menu':
            return self._convert_menu
        elif model == 'website.page':
            return self._convert_page
        else:
            _logger.error('No converter found for %s', model)

    def _update_records(self, old, new):
        # This function:
        #    create new record if not in old
        #    update old record if already exists
        #    delete old record that are not in new
        website = self.env['website'].get_current_website()
        model = old._name
        created = self.env[model]
        updated = self.env[model]
        deleted = self.env[model]

        remaining = new
        last_len = -1
        while (len(remaining) != last_len):
            last_len = len(remaining)
            for rec in remaining:
                rec_data = self._convert(model)(rec, website)
                if not rec_data:
                    _logger.info('Record queued: %s' % rec.name)
                    continue

                find = rec.with_context(active_test=False).mapped('copy_ids').filtered(lambda m: m.website_id == website)

                # special case for attachment
                # if module B override attachment from dependence A, we update it
                if not find and model == 'ir.attachment':
                    find = rec.copy_ids.search([('key', '=', rec.key), ('website_id', '=', website.id)])

                if old and model == 'ir.ui.view': # at update, ignore active field
                    rec_data.pop('active')

                if find:
                    imd = self.env['ir.model.data'].search([('model', '=', find._name), ('res_id', '=', find.id)])
                    if imd and imd.noupdate:
                        _logger.info('Noupdate set for %s (%s)' % (find, imd))
                        continue
                    find.update(rec_data)
                    updated += find
                else:
                    created += self.env[model].create(rec_data)
                remaining -= rec

        deleted = old - updated
        deleted.unlink()
        return (created, updated, deleted)

    def _load_one_theme_module(self, website, with_update=True, **kw):
        # load data from xml to template table
        old_menus = self._get_module_data('theme.website.menu').with_context(active_test=False).mapped('copy_ids').filtered(lambda m: m.website_id == website)
        old_pages = self._get_module_data('theme.website.page').with_context(active_test=False).mapped('copy_ids').filtered(lambda p: p.website_id == website)
        old_attachs = self._get_module_data('theme.ir.attachment').with_context(active_test=False).mapped('copy_ids').filtered(lambda a: a.website_id == website)
        old_views = self._get_module_data('theme.ir.ui.view').with_context(active_test=False).mapped('copy_ids').filtered(lambda v: v.website_id == website)

        if with_update:
            self.button_immediate_upgrade()

        new_menus = self._get_module_data('theme.website.menu')
        new_pages = self._get_module_data('theme.website.page')
        new_attachs = self._get_module_data('theme.ir.attachment')
        new_views = self._get_module_data('theme.ir.ui.view')

        self._update_records(old_menus, new_menus)
        self._update_records(old_pages, new_pages)
        self._update_records(old_attachs, new_attachs)
        self._update_records(old_views, new_views)

    @api.multi
    def _unload_one_theme_module(self, website):
        self.ensure_one()
        _logger.info('Unload theme %s for website %s from template.' % (self.mapped('name'), website.id))
        menus = self._get_module_data('theme.website.menu')
        menu_todel = menus.with_context(active_test=False).mapped('copy_ids').filtered(lambda m: m.website_id == website)
        menu_todel.unlink()

        pages = self._get_module_data('theme.website.page')
        pages_todel = pages.with_context(active_test=False).mapped('copy_ids').filtered(lambda p: p.website_id == website)
        pages_todel.unlink()

        attachs = self._get_module_data('theme.ir.attachment')
        attachs_todel = attachs.with_context(active_test=False).mapped('copy_ids').filtered(lambda a: a.website_id == website)
        # double check - Some records that can be orphans or no more in the template view.
        attachs_todel2 = self.env['ir.attachment'].with_context(active_test=False).search([('key', '=like', self.name + '_%'), ('website_id', '=', website.id)])
        (attachs_todel + attachs_todel2).unlink()

        views = self._get_module_data('theme.ir.ui.view')
        views_todel = views.with_context(active_test=False).mapped('copy_ids').filtered(lambda v: v.website_id == website)
        # double check - Some records that can be orphans or no more in the template view.
        views_todel2 = self.env['ir.ui.view'].with_context(active_test=False).search([('key', '=like', self.name + '_%'), ('website_id', '=', website.id)])
        (views_todel + views_todel2).unlink()

    @api.multi
    def _remove_theme_on_website(self, website):
        self.ensure_one()
        installed_deps = self + website.theme_id.upstream_dependencies(exclude_states=('',)).filtered(lambda x: x.name.startswith('theme_'))
        for mod in installed_deps:
            mod._unload_one_theme_module(website)

    @api.multi
    def _add_theme_on_website(self, website):
        self.ensure_one()
        mods_to_load = reversed(self + self.upstream_dependencies(exclude_states=('',)).filtered(lambda x: x.name.startswith('theme_')))
        for mod in mods_to_load:
            _logger.info('Load theme %s for website %s from template.' % (mod.name, website.id))
            mod._load_one_theme_module(website, with_update=False)
            self.env['theme.utils']._post_copy(mod)

    @api.multi
    def button_choose_theme(self):
        self.ensure_one()
        website = self.env['website'].get_current_website()

        # Unload previous theme
        if website.theme_id:
            website.theme_id._remove_theme_on_website(website)

        website.theme_id = self

        # create template data of missing theme
        next_action = False
        if self.state != 'installed':
            next_action = self.button_immediate_install()
            # reload registry to check if 'theme.utils'._<theme_name>_post_copy exists e.g.
            self.env.reset()
            self = self.env()[self._name].browse(self.id)

        # Copy new theme from template table to real table
        self._add_theme_on_website(website)

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
        self._load_one_theme_module(website, with_update=True)

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
