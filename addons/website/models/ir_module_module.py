# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os
from collections import OrderedDict

from odoo import api, fields, models
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
from odoo.exceptions import MissingError
from odoo.http import request

_logger = logging.getLogger(__name__)


class IrModuleModule(models.Model):
    _name = "ir.module.module"
    _description = 'Module'
    _inherit = _name

    # The order is important because of dependencies (page need view, menu need page)
    _theme_model_names = OrderedDict([
        ('ir.ui.view', 'theme.ir.ui.view'),
        ('website.page', 'theme.website.page'),
        ('website.menu', 'theme.website.menu'),
        ('ir.attachment', 'theme.ir.attachment'),
    ])
    _theme_translated_fields = {
        'theme.ir.ui.view': [('theme.ir.ui.view,arch', 'ir.ui.view,arch_db')],
        'theme.website.menu': [('theme.website.menu,name', 'website.menu,name')],
    }

    image_ids = fields.One2many('ir.attachment', 'res_id',
                                domain=[('res_model', '=', _name), ('mimetype', '=like', 'image/%')],
                                string='Screenshots', readonly=True)
    # for kanban view
    is_installed_on_current_website = fields.Boolean(compute='_compute_is_installed_on_current_website')

    def _compute_is_installed_on_current_website(self):
        """
            Compute for every theme in ``self`` if the current website is using it or not.

            This method does not take dependencies into account, because if it did, it would show
            the current website as having multiple different themes installed at the same time,
            which would be confusing for the user.
        """
        for module in self:
            module.is_installed_on_current_website = module == self.env['website'].get_current_website().theme_id

    def write(self, vals):
        """
            Override to correctly upgrade themes after upgrade/installation of modules.

            # Install

                If this theme wasn't installed before, then load it for every website
                for which it is in the stream.

                eg. The very first installation of a theme on a website will trigger this.

                eg. If a website uses theme_A and we install sale, then theme_A_sale will be
                    autoinstalled, and in this case we need to load theme_A_sale for the website.

            # Upgrade

                There are 2 cases to handle when upgrading a theme:

                * When clicking on the theme upgrade button on the interface,
                    in which case there will be an http request made.

                    -> We want to upgrade the current website only, not any other.

                * When upgrading with -u, in which case no request should be set.

                    -> We want to upgrade every website using this theme.
        """
        for module in self:
            if module.name.startswith('theme_') and vals.get('state') == 'installed':
                _logger.info('Module %s has been loaded as theme template (%s)' % (module.name, module.state))

                if module.state in ['to install', 'to upgrade']:
                    websites_to_update = module._theme_get_stream_website_ids()

                    if module.state == 'to upgrade' and request:
                        Website = self.env['website']
                        current_website = Website.get_current_website()
                        websites_to_update = current_website if current_website in websites_to_update else Website

                    for website in websites_to_update:
                        module._theme_load(website)

        return super(IrModuleModule, self).write(vals)

    def _get_module_data(self, model_name):
        """
            Return every theme template model of type ``model_name`` for every theme in ``self``.

            :param model_name: string with the technical name of the model for which to get data.
                (the name must be one of the keys present in ``_theme_model_names``)
            :return: recordset of theme template models (of type defined by ``model_name``)
        """
        theme_model_name = self._theme_model_names[model_name]
        IrModelData = self.env['ir.model.data']
        records = self.env[theme_model_name]

        for module in self:
            imd_ids = IrModelData.search([('module', '=', module.name), ('model', '=', theme_model_name)]).mapped('res_id')
            records |= self.env[theme_model_name].with_context(active_test=False).browse(imd_ids)
        return records

    def _update_records(self, model_name, website):
        """
            This method:

            - Find and update existing records.

                For each model, overwrite the fields that are defined in the template (except few
                cases such as active) but keep inherited models to not lose customizations.

            - Create new records from templates for those that didn't exist.

            - Remove the models that existed before but are not in the template anymore.

                See _theme_cleanup for more information.


            There is a special 'while' loop around the 'for' to be able queue back models at the end
            of the iteration when they have unmet dependencies. Hopefully the dependency will be
            found after all models have been processed, but if it's not the case an error message will be shown.


            :param model_name: string with the technical name of the model to handle
                (the name must be one of the keys present in ``_theme_model_names``)
            :param website: ``website`` model for which the records have to be updated

            :raise MissingError: if there is a missing dependency.
        """
        self.ensure_one()

        remaining = self._get_module_data(model_name)
        last_len = -1
        while (len(remaining) != last_len):
            last_len = len(remaining)
            for rec in remaining:
                rec_data = rec._convert_to_base_model(website)
                if not rec_data:
                    _logger.info('Record queued: %s' % rec.display_name)
                    continue

                find = rec.with_context(active_test=False).mapped('copy_ids').filtered(lambda m: m.website_id == website)

                # special case for attachment
                # if module B override attachment from dependence A, we update it
                if not find and model_name == 'ir.attachment':
                    find = rec.copy_ids.search([('key', '=', rec.key), ('website_id', '=', website.id)])

                if find:
                    imd = self.env['ir.model.data'].search([('model', '=', find._name), ('res_id', '=', find.id)])
                    if imd and imd.noupdate:
                        _logger.info('Noupdate set for %s (%s)' % (find, imd))
                    else:
                        # at update, ignore active field
                        if 'active' in rec_data:
                            rec_data.pop('active')
                        find.update(rec_data)
                        self._post_copy(rec, find)
                else:
                    new_rec = self.env[model_name].create(rec_data)
                    self._post_copy(rec, new_rec)

                remaining -= rec

        if len(remaining):
            error = 'Error - Remaining: %s' % remaining.mapped('display_name')
            _logger.error(error)
            raise MissingError(error)

        self._theme_cleanup(model_name, website)

    def _post_copy(self, old_rec, new_rec):
        self.ensure_one()
        translated_fields = self._theme_translated_fields.get(old_rec._name, [])
        for (src_field, dst_field) in translated_fields:
            self._cr.execute("""INSERT INTO ir_translation (lang, src, name, res_id, state, value, type, module)
                                SELECT t.lang, t.src, %s, %s, t.state, t.value, t.type, t.module
                                FROM ir_translation t
                                WHERE name = %s
                                  AND res_id = %s
                                ON CONFLICT DO NOTHING""",
                             (dst_field, new_rec.id, src_field, old_rec.id))

    def _theme_load(self, website):
        """
            For every type of model in ``self._theme_model_names``, and for every theme in ``self``:
            create/update real models for the website ``website`` based on the theme template models.

            :param website: ``website`` model on which to load the themes
        """
        for module in self:
            _logger.info('Load theme %s for website %s from template.' % (module.mapped('name'), website.id))

            for model_name in self._theme_model_names:
                module._update_records(model_name, website)

            self.env['theme.utils'].with_context(website_id=website.id)._post_copy(module)

    def _theme_unload(self, website):
        """
            For every type of model in ``self._theme_model_names``, and for every theme in ``self``:
            remove real models that were generated based on the theme template models
            for the website ``website``.

            :param website: ``website`` model on which to unload the themes
        """
        for module in self:
            _logger.info('Unload theme %s for website %s from template.' % (self.mapped('name'), website.id))

            for model_name in self._theme_model_names:
                template = self._get_module_data(model_name)
                models = template.with_context(**{'active_test': False, MODULE_UNINSTALL_FLAG: True}).mapped('copy_ids').filtered(lambda m: m.website_id == website)
                models.unlink()
                self._theme_cleanup(model_name, website)

    def _theme_cleanup(self, model_name, website):
        """
            Remove orphan models of type ``model_name`` from the current theme and
            for the website ``website``.

            We need to compute it this way because if the upgrade (or deletion) of a theme module
            removes a model template, then in the model itself the variable
            ``theme_template_id`` will be set to NULL and the reference to the theme being removed
            will be lost. However we do want the ophan to be deleted from the website when
            we upgrade or delete the theme from the website.

            ``website.page`` and ``website.menu`` don't have ``key`` field so we don't clean them.
            TODO in master: add a field ``theme_id`` on the models to more cleanly compute orphans.

            :param model_name: string with the technical name of the model to cleanup
                (the name must be one of the keys present in ``_theme_model_names``)
            :param website: ``website`` model for which the models have to be cleaned

        """
        self.ensure_one()
        model = self.env[model_name]

        if model_name in ('website.page', 'website.menu'):
            return model
        # use active_test to also unlink archived models
        # and use MODULE_UNINSTALL_FLAG to also unlink inherited models
        orphans = model.with_context(**{'active_test': False, MODULE_UNINSTALL_FLAG: True}).search([
            ('key', '=like', self.name + '.%'),
            ('website_id', '=', website.id),
            ('theme_template_id', '=', False),
        ])
        orphans.unlink()

    def _theme_get_upstream(self):
        """
            Return installed upstream themes.

            :return: recordset of themes ``ir.module.module``
        """
        self.ensure_one()
        return self.upstream_dependencies(exclude_states=('',)).filtered(lambda x: x.name.startswith('theme_'))

    def _theme_get_downstream(self):
        """
            Return installed downstream themes that starts with the same name.

            eg. For theme_A, this will return theme_A_sale, but not theme_B even if theme B
                depends on theme_A.

            :return: recordset of themes ``ir.module.module``
        """
        self.ensure_one()
        return self.downstream_dependencies().filtered(lambda x: x.name.startswith(self.name))

    def _theme_get_stream_themes(self):
        """
            Returns all the themes in the stream of the current theme.

            First find all its downstream themes, and all of the upstream themes of both
            sorted by their level in hierarchy, up first.

            :return: recordset of themes ``ir.module.module``
        """
        self.ensure_one()
        all_mods = self + self._theme_get_downstream()
        for down_mod in self._theme_get_downstream() + self:
            for up_mod in down_mod._theme_get_upstream():
                all_mods = up_mod | all_mods
        return all_mods

    def _theme_get_stream_website_ids(self):
        """
            Websites for which this theme (self) is in the stream (up or down) of their theme.

            :return: recordset of websites ``website``
        """
        self.ensure_one()
        websites = self.env['website']
        for website in websites.search([('theme_id', '!=', False)]):
            if self in website.theme_id._theme_get_stream_themes():
                websites |= website
        return websites

    def _theme_upgrade_upstream(self):
        """ Upgrade the upstream dependencies of a theme, and install it if necessary. """
        def install_or_upgrade(theme):
            if theme.state != 'installed':
                theme.button_install()
            themes = theme + theme._theme_get_upstream()
            themes.filtered(lambda m: m.state == 'installed').button_upgrade()

        self._button_immediate_function(install_or_upgrade)

    @api.model
    def _theme_remove(self, website):
        """
            Remove from ``website`` its current theme, including all the themes in the stream.

            The order of removal will be reverse of installation to handle dependencies correctly.

            :param website: ``website`` model for which the themes have to be removed
        """
        if not website.theme_id:
            return

        for theme in reversed(website.theme_id._theme_get_stream_themes()):
            theme._theme_unload(website)
        website.theme_id = False

    def button_choose_theme(self):
        """
            Remove any existing theme on the current website and install the theme ``self`` instead.

            The actual loading of the theme on the current website will be done
            automatically on ``write`` thanks to the upgrade and/or install.

            When installating a new theme, upgrade the upstream chain first to make sure
            we have the latest version of the dependencies to prevent inconsistencies.

            :return: dict with the next action to execute
        """
        self.ensure_one()
        website = self.env['website'].get_current_website()

        self._theme_remove(website)

        # website.theme_id must be set before upgrade/install to trigger the load in ``write``
        website.theme_id = self

        # this will install 'self' if it is not installed yet
        self._theme_upgrade_upstream()

        return website.button_go_website()

    def button_remove_theme(self):
        """Remove the current theme of the current website."""
        website = self.env['website'].get_current_website()
        self._theme_remove(website)

    def button_refresh_theme(self):
        """
            Refresh the current theme of the current website.

            To refresh it, we only need to upgrade the modules.
            Indeed the (re)loading of the theme will be done automatically on ``write``.
        """
        website = self.env['website'].get_current_website()
        website.theme_id._theme_upgrade_upstream()

    @api.model
    def update_list(self):
        res = super(IrModuleModule, self).update_list()
        self.update_theme_images()
        return res

    @api.model
    def update_theme_images(self):
        IrAttachment = self.env['ir.attachment']
        existing_urls = IrAttachment.search_read([['res_model', '=', self._name], ['type', '=', 'url']], ['url'])
        existing_urls = [url_wrapped['url'] for url_wrapped in existing_urls]

        themes = self.env['ir.module.module'].with_context(active_test=False).search([
            ('category_id', 'child_of', self.env.ref('base.module_category_theme').id),
        ], order='name')

        for theme in themes:
            terp = self.get_module_info(theme.name)
            images = terp.get('images', [])
            for image in images:
                image_path = os.path.join(theme.name, image)
                if image_path not in existing_urls:
                    image_name = os.path.basename(image_path)
                    IrAttachment.create({
                        'type': 'url',
                        'name': image_name,
                        'url': image_path,
                        'res_model': self._name,
                        'res_id': theme.id,
                    })
