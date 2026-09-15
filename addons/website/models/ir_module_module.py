# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import werkzeug

from odoo import api, fields, models
from odoo.tools import SQL, split_every
from odoo.tools.constants import IN_MAX
from odoo.tools.translate import StoredTranslations

_logger = logging.getLogger(__name__)


class IrModuleModule(models.Model):
    _name = 'ir.module.module'
    _description = 'Module'
    _inherit = ['ir.module.module']

    image_ids = fields.One2many('ir.attachment', 'res_id',
                                domain=[('res_model', '=', 'ir.module.module'), ('mimetype', '=like', 'image/%')],
                                string='Screenshots', readonly=True)
    # for kanban view
    is_installed_on_current_website = fields.Boolean(compute='_compute_is_installed_on_current_website')

    @api.depends_context('website_id', 'host_id')
    def _compute_is_installed_on_current_website(self):
        """
            Compute for every theme in ``self`` if the current website is using it or not.

            This method does not take dependencies into account, because if it did, it would show
            the current website as having multiple different themes installed at the same time,
            which would be confusing for the user.
        """
        website = self.env.website or self.env['website'].browse(self.env.context.get('host_id'))
        for module in self:
            module.is_installed_on_current_website = module == website.theme_id

    def _button_immediate_function(self, func):
        website = self.env.website or self.env['website'].browse(self.env.context.get('host_id'))
        self.env['ir.config_parameter'].sudo().set_int('website.apply_new_theme', website.id)
        res = super()._button_immediate_function(func)
        self.env['ir.config_parameter'].sudo().set_int('website.apply_new_theme', False)
        return res

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
        ThemeEngine = self.env['theme.engine']
        for module in self:
            if module.name.startswith('theme_') and vals.get('state') == 'installed':
                _logger.info('Module %s has been loaded as theme template (%s)' % (module.name, module.state))

                if module.state in ['to install', 'to upgrade']:
                    websites_to_update = module._theme_get_stream_website_ids()
                    if module.state == 'to upgrade' and (website_restriction := int(self.env['ir.config_parameter'].sudo().get_int('website.apply_new_theme', 0))):
                        if website_restriction in websites_to_update.ids:
                            websites_to_update = websites_to_update.browse(website_restriction)
                        else:
                            websites_to_update = websites_to_update.browse()

                    for website in websites_to_update:
                        ThemeEngine._theme_load(module, website)

        return super(IrModuleModule, self).write(vals)

    def _theme_get_upstream(self):
        """
            Return installed upstream themes.

            :return: recordset of themes ``ir.module.module``
        """
        self.ensure_one()
        return self.upstream_dependencies(exclude_states=()).filtered(lambda x: x.name.startswith('theme_'))

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
        if not self.env.user.has_group('website.group_website_restricted_editor'):
            raise werkzeug.exceptions.Forbidden()

        def install_or_upgrade(theme):
            if theme.state != 'installed':
                theme.button_install()
            themes = theme + theme._theme_get_upstream()
            themes.filtered(lambda m: m.state == 'installed').button_upgrade()

        self.sudo()._button_immediate_function(install_or_upgrade)

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
        website = self.env.website or self.env['website'].browse(self.env.context.get('host_id'))
        website.ensure_one()

        self.env['theme.engine']._theme_remove(website)

        # website.theme_id must be set before upgrade/install to trigger the load in ``write``
        website.theme_id = self

        # this will install 'self' if it is not installed yet
        self._theme_upgrade_upstream()
        self.env['theme.utils'].with_context(website_id=website.id)._post_copy(self)

        result = website.button_go_website()
        return result

    def button_remove_theme(self):
        """Remove the current theme of the current website."""
        website = self.env.website or self.env['website'].browse(self.env.context.get('host_id'))
        self.env['theme.engine']._theme_remove(website)

    def button_refresh_theme(self):
        """
            Refresh the current theme of the current website.

            To refresh it, we only need to upgrade the modules.
            Indeed the (re)loading of the theme will be done automatically on ``write``.
        """
        website = self.env.website or self.env['website'].browse(self.env.context.get('host_id'))
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
        existing_urls = {url_wrapped['url'] for url_wrapped in existing_urls}

        themes = self.env['ir.module.module'].with_context(active_test=False).search([
            ('category_id', 'child_of', self.env.ref('base.module_category_theme').id),
        ], order='name')

        for theme in themes:
            terp = self.get_module_info(theme.name)
            images = terp.get('images', [])
            image_paths = ['/%s/%s' % (theme.name, image) for image in images]
            if all(image_path in existing_urls for image_path in image_paths):
                continue
            # Images creation order must be the order specified in the manifest
            for image_path in image_paths:
                image_name = image_path.split('/')[-1]
                IrAttachment.create({
                    'type': 'url',
                    'name': image_name,
                    'url': image_path,
                    'res_model': self._name,
                    'res_id': theme.id,
                })

    def get_themes_domain(self):
        """Returns the 'ir.module.module' search domain matching all available themes."""
        def get_id(model_id):
            return self.env['ir.model.data']._xmlid_to_res_id(model_id)
        return [
            ('state', '!=', 'uninstallable'),
            ('category_id', 'not in', [
                get_id('base.module_category_hidden'),
                get_id('base.module_category_theme_hidden'),
            ]),
            '|',
            ('category_id', '=', get_id('base.module_category_theme')),
            ('category_id.parent_id', '=', get_id('base.module_category_theme'))
        ]

    def _check(self):
        super()._check()
        View = self.env['ir.ui.view']
        website_views_to_adapt = getattr(self.pool, 'website_views_to_adapt', [])
        if website_views_to_adapt:
            for view_replay in website_views_to_adapt:
                cow_view = View.browse(view_replay[0])
                View._load_records_write_on_cow(cow_view, view_replay[1], view_replay[2])
            self.pool.website_views_to_adapt.clear()

    @api.model
    def _load_module_terms(self, modules, langs, overwrite=False):
        """ Add missing website specific translation """
        res = super()._load_module_terms(modules, langs, overwrite=overwrite)

        if not langs or langs == ['en_US'] or not modules:
            return res

        # Add specific view translations

        # use the translation dic of the generic to translate the specific
        self.env.cr.flush()
        View = self.env['ir.ui.view'].with_context(lang='en_US')
        env_en = View.env
        field = self.env['ir.ui.view']._fields['arch_db']
        batch_size = IN_MAX // 10
        self.env.cr.execute(""" SELECT generic.arch_db, specific.arch_db, specific.id
                                          FROM ir_ui_view generic
                                         INNER JOIN ir_ui_view specific
                                            ON generic.key = specific.key
                                         WHERE generic.website_id IS NULL AND generic.type = 'qweb'
                                         AND specific.website_id IS NOT NULL
                                         AND generic.arch_db IS NOT NULL
                                         AND specific.arch_db IS NOT NULL
                            """)
        while batch := self.env.cr.fetchmany(batch_size):
            for generic_arch_db, specific_arch_db, specific_id in batch:
                langs_update = (langs & generic_arch_db.keys()) - {'en_US'}
                if not langs_update:
                    continue
                generic_arch_db = StoredTranslations(generic_arch_db)
                specific_arch_db = StoredTranslations(specific_arch_db)
                # extract {lang: {src_term: translated_term}} from the generic view
                term_updates = generic_arch_db.extract_term_translations(env_en, field, 'en_US', target_langs=langs_update)
                new_specific_arch_db = specific_arch_db.translated(
                    env_en, field, 'en_US', term_updates, overwrite=overwrite,
                    delay_translations=True,
                )
                # like `Translaitonimporter.save()` we bypass the ORM(`View.write()`)
                field._update_cache(View.with_context(prefetch_langs=True).browse(specific_id), new_specific_arch_db, dirty=True)
        default_menu = self.env.ref('website.main_menu', raise_if_not_found=False)
        if not default_menu:
            return res

        lang_value_list = [SQL("%(lang)s, o_menu.name->>%(lang)s", lang=lang) for lang in langs if lang != 'en_US']
        update_jsonb_list = [SQL('jsonb_build_object(%s)', SQL(', ').join(items)) for items in split_every(50, lang_value_list)]
        update_jsonb = SQL(' || ').join(update_jsonb_list)
        o_menu_name = SQL('menu.name || %s' if overwrite else '%s || menu.name', update_jsonb)
        self.env.cr.execute(SQL(
            """
            UPDATE website_menu menu
               SET name = %(o_menu_name)s
              FROM website_menu o_menu
             INNER JOIN website_menu s_menu
                ON o_menu.name->>'en_US' = s_menu.name->>'en_US'
             INNER JOIN website_menu root_menu
                ON s_menu.parent_id = root_menu.id AND root_menu.parent_id IS NULL
             WHERE o_menu.website_id IS NULL AND o_menu.parent_id = %(default_menu_id)s
               AND s_menu.website_id IS NOT NULL
               AND menu.id = s_menu.id
            """,
            o_menu_name=o_menu_name,
            default_menu_id=default_menu.id
        ))

        return res
