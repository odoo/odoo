# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from collections import OrderedDict

import werkzeug

from odoo import api, models
from odoo.exceptions import MissingError
from odoo.modules import Manifest

_logger = logging.getLogger(__name__)


class ThemeEngine(models.AbstractModel):
    """ Turns what a theme module ships into real records.

        A theme module holds ``theme.*`` template records; this model copies
        them into the records of a given website, removes them again, and
        cleans up the orphans left behind by a theme update.

        It also generates the primary snippet and page templates declared in a
        module manifest, which is unrelated to any website.
    """
    _name = 'theme.engine'
    _description = 'Theme Engine'

    # The order is important because of dependencies (page need view, menu need page)
    _theme_model_names = OrderedDict([
        ('ir.ui.view', 'theme.ir.ui.view'),
        ('ir.asset', 'theme.ir.asset'),
        ('website.page', 'theme.website.page'),
        ('website.menu', 'theme.website.menu'),
        ('ir.attachment', 'theme.ir.attachment'),
    ])
    _theme_translated_fields = {
        'theme.ir.ui.view': [('theme.ir.ui.view,arch', 'ir.ui.view,arch_db')],
        'theme.website.menu': [('theme.website.menu,name', 'website.menu,name')],
        'theme.website.page': [('theme.website.page,url', 'website.page,url')],
    }

    @api.model
    def _get_module_data(self, themes, model_name):
        """
            Return every theme template model of type ``model_name`` for every theme in ``themes``.

            :param themes: recordset of themes ``ir.module.module`` to get the data of
            :param model_name: string with the technical name of the model for which to get data.
                (the name must be one of the keys present in ``_theme_model_names``)
            :return: recordset of theme template models (of type defined by ``model_name``)
        """
        if not self.env.user.has_group('website.group_website_restricted_editor'):
            raise werkzeug.exceptions.Forbidden()

        themes_sudo = themes.sudo()

        theme_model_name = self._theme_model_names[model_name]
        IrModelData = self.env['ir.model.data'].sudo()
        records = self.env[theme_model_name].sudo()

        for module in themes_sudo:
            imd_ids = IrModelData.search([
                ('module', '=', module.name),
                ('model', '=', theme_model_name),
                ('res_id', '!=', False),
            ]).mapped('res_id')
            records |= self.env[theme_model_name].sudo().with_context(active_test=False).browse(imd_ids)
        return records

    @api.model
    def _update_records(self, theme, model_name, website):
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


            :param theme: ``ir.module.module`` theme whose records have to be updated
            :param model_name: string with the technical name of the model to handle
                (the name must be one of the keys present in ``_theme_model_names``)
            :param website: ``website`` model for which the records have to be updated

            :raise MissingError: if there is a missing dependency.
        """
        theme.ensure_one()

        remaining = self._get_module_data(theme, model_name)
        last_len = -1
        while (len(remaining) != last_len):
            last_len = len(remaining)
            for rec in remaining:
                rec_data = rec._convert_to_base_model(website)
                if not rec_data:
                    _logger.info('Record queued: %s', rec.display_name)
                    continue

                find = rec.with_context(active_test=False).mapped('copy_ids').filtered(lambda m: m.website_id == website)

                # special case for attachment
                # if module B override attachment from dependence A, we update it
                if not find and model_name == 'ir.attachment':
                    # In master, a unique constraint over (theme_template_id, website_id)
                    # will be introduced, thus ensuring unicity of 'find'
                    find = rec.copy_ids.search([('key', '=', rec.key), ('website_id', '=', website.id), ("original_id", "=", False)])

                if find:
                    imd = self.env['ir.model.data'].search([('model', '=', find._name), ('res_id', '=', find.id)])
                    if imd and imd.noupdate:
                        _logger.info('Noupdate set for %s (%s)', find, imd)
                    else:
                        # at update, ignore active field
                        if 'active' in rec_data:
                            rec_data.pop('active')
                        if model_name == 'ir.ui.view' and (find.arch_updated or find.arch == rec_data['arch']):
                            rec_data.pop('arch')
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

        self._theme_cleanup(theme, model_name, website)

    @api.model
    def _post_copy(self, old_rec, new_rec):
        translated_fields = self._theme_translated_fields.get(old_rec._name, [])
        cur_lang = self.env.lang or 'en_US'
        valid_langs = {code for code, _ in self.env['res.lang'].get_installed()} | {'en_US'}
        old_rec.flush_recordset()
        for (src_field, dst_field) in translated_fields:
            __, src_fname = src_field.split(',')
            dst_mname, dst_fname = dst_field.split(',')
            if dst_mname != new_rec._name:
                continue
            old_field = old_rec._fields[src_fname]
            old_stored_translations = old_rec._get_stored_translations(src_fname)
            if not old_stored_translations:
                continue
            if old_field.translate is True:
                if old_rec[src_fname] != new_rec[dst_fname]:
                    continue
                new_rec.update_field_translations(dst_fname, {
                    k: v for k, v in old_stored_translations.items() if k in valid_langs and k != cur_lang
                })
            else:
                # {lang: {old_term: new_term}}
                translations = old_stored_translations.extract_term_translations(
                    self.env, old_field, 'en_US',
                )
                new_rec.with_context(install_filename='dummy').update_field_translations(
                    dst_fname, translations, source_lang='en_US',
                )

    @api.model
    def _theme_load(self, themes, website):
        """
            For every type of model in ``self._theme_model_names``, and for every theme in ``themes``:
            create/update real models for the website ``website`` based on the theme template models.

            :param themes: recordset of themes ``ir.module.module`` to load
            :param website: ``website`` model on which to load the themes
        """
        for module in themes:
            _logger.info('Load theme %s for website %s from template.', module.mapped('name'), website.id)

            for model_name in self._theme_model_names:
                self._update_records(module, model_name, website)

            if self.env.context.get('apply_new_theme'):
                # TODO Kept for backward compatibility with design-themes tests
                # and web_studio. This could become a parameter in master.
                self.env['theme.utils'].with_context(website_id=website.id)._post_copy(module)

    @api.model
    def _theme_unload(self, themes, website):
        """
            For every type of model in ``self._theme_model_names``, and for every theme in ``themes``:
            remove real models that were generated based on the theme template models
            for the website ``website``.

            :param themes: recordset of themes ``ir.module.module`` to unload
            :param website: ``website`` model on which to unload the themes
        """
        for module in themes:
            _logger.info('Unload theme %s for website %s from template.', themes.mapped('name'), website.id)

            for model_name in self._theme_model_names:
                template = self._get_module_data(module, model_name)
                models_ = template.with_context(active_test=False, force_delete=True).mapped('copy_ids').filtered(lambda m: m.website_id == website)
                models_.unlink()
                self._theme_cleanup(module, model_name, website)

    @api.model
    def _theme_cleanup(self, theme, model_name, website):
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

            :param theme: ``ir.module.module`` theme whose orphans have to be removed
            :param model_name: string with the technical name of the model to cleanup
                (the name must be one of the keys present in ``_theme_model_names``)
            :param website: ``website`` model for which the models have to be cleaned

        """
        if not self.env.user.has_group('website.group_website_restricted_editor'):
            raise werkzeug.exceptions.Forbidden()

        theme.ensure_one()
        model_sudo = self.env[model_name].sudo()

        if model_name in ('website.page', 'website.menu'):
            return model_sudo
        # use active_test to also unlink archived models
        # and use 'force_delete' to also unlink inherited models
        orphans = model_sudo.with_context(active_test=False, force_delete=True).search([
            ('key', '=like', theme.name + '.%'),
            ('website_id', '=', website.id),
            ('theme_template_id', '=', False),
        ])
        orphans.unlink()

    @api.model
    def _theme_remove(self, website):
        """
            Remove from ``website`` its current theme, including all the themes in the stream.

            The order of removal will be reverse of installation to handle dependencies correctly.

            :param website: ``website`` model for which the themes have to be removed
        """
        # _theme_remove is the entry point of any change of theme for a website
        # (either removal or installation of a theme and its dependencies). In
        # either case, we need to reset some default configuration before.
        self.env['theme.utils'].with_context(website_id=website.id)._reset_default_config()

        if not website.theme_id:
            return

        for theme in reversed(website.theme_id._theme_get_stream_themes()):
            self._theme_unload(theme, website)
        website.theme_id = False

    # ----------------------------------------------------------------
    # New page templates
    # ----------------------------------------------------------------

    @api.model
    def _create_model_data(self, views):
        """ Creates model data records for newly created view records.

            :param views: views for which model data must be created
        """
        # The generated templates are set as noupdate in order to avoid that
        # _process_end deletes them.
        # In case some of them require an XML definition in the future,
        # an upgrade script will be needed to temporarily make those
        # records updatable.
        self.env['ir.model.data'].create([{
            'name': view.key.split('.')[1],
            'module': view.key.split('.')[0],
            'model': 'ir.ui.view',
            'res_id': view.id,
            'noupdate': True,
        } for view in views])

    @api.model
    def _generate_primary_snippet_templates(self, module_ids):
        """ Generates snippet templates hierarchy based on manifest entries for
            use in the configurator and when creating new pages from templates.

            :param module_ids: ids of the ``ir.module.module`` to generate for
        """
        module = self.env['ir.module.module'].browse(module_ids).ensure_one()

        def split_key(snippet_key):
            """ Snippets xmlid can be written without the module part, meaning
                it is a shortcut for a website module snippet.

                :param snippet_key: xmlid with or without the module part
                    'website' is assumed to be the default module
                :return: module and key extracted from the snippet_key
            """
            return snippet_key.split('.') if '.' in snippet_key else ('website', snippet_key)

        def create_missing_views(create_values):
            """ Creates the snippet primary view records that do not exist yet.

                :param create_values: values of records to create
                :return: number of created records
            """
            # Defensive code (low effort): `if values` should always be set
            create_values = [values for values in create_values if values]

            keys = [values['key'] for values in create_values]
            existing_primary_template_keys = self.env['ir.ui.view'].with_context(active_test=False).search_fetch([
                ('mode', '=', 'primary'), ('key', 'in', keys),
            ], ['key']).mapped('key')
            missing_create_values = [values for values in create_values if values['key'] not in existing_primary_template_keys]
            missing_records = self.env['ir.ui.view'].with_context(no_cow=True).create(missing_create_values)
            self._create_model_data(missing_records)
            return len(missing_records)

        def get_create_vals(name, snippet_key, parent_wrap, new_wrap):
            """ Returns the create values for the new primary template of the
                snippet having snippet_key as its base key, having a new key
                formatted with new_wrap, and extending a parent with the key
                formatted with parent_wrap.

                :param name: name
                :param snippet_key: xmlid of the base block
                :param parent_wrap: string pattern used to format the
                    snippet_key's second part to reach the parent key
                :param new_wrap: string pattern used to format the
                    snippet_key's second part to reach the new key
                :return: create values for the new record
            """
            module, xmlid = split_key(snippet_key)
            parent_key = f'{module}.{parent_wrap % xmlid}'
            # Equivalent to using an already cached ref, without failing on
            # missing key - because the parent records have just been created.
            parent_id = self.env['ir.model.data']._xmlid_to_res_model_res_id(parent_key, False)
            if not parent_id:
                _logger.warning("No such snippet template: %r", parent_key)
                return None
            return {
                'name': name,
                'key': f'{module}.{new_wrap % xmlid}',
                'inherit_id': parent_id[1],
                'mode': 'primary',
                'type': 'qweb',
                'arch': '<t/>',
            }

        def get_distinct_snippet_names(structure):
            """ Returns the distinct leaves of the structure (tree leaf's list
                elements).

                :param structure: dict or list or snippet names
                :return: distinct snippet names
            """
            items = []
            for value in structure.values():
                if isinstance(value, list):
                    items.extend(value)
                else:
                    items.extend(get_distinct_snippet_names(value))
            return set(items)

        create_count = 0
        manifest = Manifest.for_addon(module.name)

        # ------------------------------------------------------------
        # Configurator
        # ------------------------------------------------------------

        configurator_snippets = dict(manifest.get('configurator_snippets', {}))
        installed_modules = self.env['ir.module.module']._installed()

        def add_addons_snippets(addons):
            """ Add installable addon snippets to the configurator snippets. """
            for module_name, pages in addons.items():
                # A snippet such as `website_sale.x` can only be generated
                # once `website_sale` exists, or while installing it.
                if module_name not in installed_modules and module_name != module.name:
                    continue
                for page, snippets_to_insert in pages.items():
                    snippets = configurator_snippets.setdefault(page, [])
                    dynamic_snippets = [snippet for snippet, *_ in snippets_to_insert]
                    configurator_snippets[page] = list(dict.fromkeys(snippets + dynamic_snippets))

        # This covers themes being installed while optional addon modules such
        # as `website_sale` are already installed.
        add_addons_snippets(manifest.get('configurator_snippets_addons', {}))

        website = self.env.website or self.env['website'].browse(self.env.context.get('host_id'))
        theme = website.theme_id
        if theme and theme.name != module.name:
            # Another module is being installed after the theme was selected.
            # Only include the theme addon snippets targeting this module.
            theme_manifest = Manifest.for_addon(theme.name)
            if theme_manifest:
                theme_addons = theme_manifest.get('configurator_snippets_addons', {})
                addons = {module.name: theme_addons.get(module.name, {})}
                add_addons_snippets(addons)

        # Generate general configurator snippet templates
        create_values = []
        # Every distinct snippet name across all configurator pages.
        for snippet_name in get_distinct_snippet_names(configurator_snippets):
            create_values.append(get_create_vals(
                f"Snippet {snippet_name!r} for pages generated by the configurator",
                snippet_name, '%s', 'configurator_%s'
            ))
        create_count += create_missing_views(create_values)

        # Generate configurator snippet templates for specific pages
        create_values = []
        for page_name, page_snippets in configurator_snippets.items():
            for snippet_name in set(page_snippets):
                create_values.append(get_create_vals(
                    f"Snippet {snippet_name!r} for {page_name!r} pages generated by the configurator",
                    snippet_name, 'configurator_%s', f'configurator_{page_name}_%s'
                ))
        create_count += create_missing_views(create_values)

        # ------------------------------------------------------------
        # New page templates
        # ------------------------------------------------------------

        templates = manifest.get('new_page_templates', {})

        # Generate general new page snippet templates
        create_values = []
        # Every distinct snippet name across all new page templates.
        for snippet_name in get_distinct_snippet_names(templates):
            create_values.append(get_create_vals(
                f"Snippet {snippet_name!r} for new page templates",
                snippet_name, '%s', 'new_page_template_%s'
            ))
        create_count += create_missing_views(create_values)

        # Generate new page snippet templates for new page template groups
        create_values = []
        for group in templates:
            # Every distinct snippet name across all new page templates of group.
            for snippet_name in get_distinct_snippet_names(templates[group]):
                create_values.append(get_create_vals(
                    f"Snippet {snippet_name!r} for new page {group!r} templates",
                    snippet_name, 'new_page_template_%s', f'new_page_template_{group}_%s'
                ))
        create_count += create_missing_views(create_values)

        # Generate new page snippet templates for specific new page templates within groups
        create_values = []
        for group in templates:
            for template_name in templates[group]:
                for snippet_name in templates[group][template_name]:
                    create_values.append(get_create_vals(
                        f"Snippet {snippet_name!r} for new page {group!r} template {template_name!r}",
                        snippet_name, f'new_page_template_{group}_%s', f'new_page_template_{group}_{template_name}_%s'
                    ))
        create_count += create_missing_views(create_values)

        if create_count:
            _logger.info("Generated %s primary snippet templates for %r", create_count, module.name)

    @api.model
    def _generate_primary_page_templates(self, module_ids):
        """ Generates page templates based on manifest entries.

            :param module_ids: ids of the ``ir.module.module`` to generate for
        """
        module = self.env['ir.module.module'].browse(module_ids).ensure_one()
        View = self.env['ir.ui.view']
        manifest = Manifest.for_addon(module.name)
        templates = manifest['new_page_templates']

        # TODO Find a way to create theme and other module's template patches
        # Create or update template views per group x key
        create_values = []
        for group in templates:
            for template_name in templates[group]:
                xmlid = f'{module.name}.new_page_template_sections_{group}_{template_name}'
                wrapper = f'%s.new_page_template_{group}_{template_name}_%s'
                calls = '\n    '.join([
                    f'''<t t-snippet-call="{wrapper % (snippet_key.split('.') if '.' in snippet_key else ('website', snippet_key))}"/>'''
                    for snippet_key in templates[group][template_name]
                ])
                create_values.append({
                    'name': f"New page template: {template_name!r} in {group!r}",
                    'type': 'qweb',
                    'key': xmlid,
                    'arch': f'<div id="wrap">\n    {calls}\n</div>',
                })
        keys = [values['key'] for values in create_values]
        existing_primary_templates = View.search_read([('mode', '=', 'primary'), ('key', 'in', keys)], ['key'])
        existing_primary_template_keys = {data['key']: data['id'] for data in existing_primary_templates}
        missing_create_values = []
        update_count = 0
        for create_value in create_values:
            if create_value['key'] in existing_primary_template_keys:
                View.browse(existing_primary_template_keys[create_value['key']]).with_context(no_cow=True).write({
                    'arch': create_value['arch'],
                })
                update_count += 1
            else:
                missing_create_values.append(create_value)
        if missing_create_values:
            missing_records = View.create(missing_create_values)
            self._create_model_data(missing_records)
            _logger.info('Generated %s primary page templates for %r', len(missing_create_values), module.name)
        if update_count:
            _logger.info('Updated %s primary page templates for %r', update_count, module.name)
