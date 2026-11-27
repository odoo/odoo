# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models
from odoo.exceptions import AccessError
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

    def write(self, vals):
        """
            Override to load a theme on the websites using it after it is installed
            or upgraded.

            Upgrading a theme reloads it on every website using it. Applying a theme on
            a website is not a module operation, see ``theme.utils._theme_apply``.
        """
        ThemeUtils = self.env['theme.utils']
        for module in self:
            if module.name.startswith('theme_') and vals.get('state') == 'installed':
                _logger.info('Module %s has been loaded as theme template (%s)' % (module.name, module.state))

                if module.state in ['to install', 'to upgrade']:
                    websites_to_update = self.env['website'].search([('theme_id', '=', module.id)])
                    for website in websites_to_update:
                        ThemeUtils._theme_load(module, website)

        return super(IrModuleModule, self).write(vals)

    def button_choose_theme(self):
        """
            Remove any existing theme on the current website and apply the theme ``self`` instead.

            The theme module is installed first if it is missing. Applying it on the
            website is a separate step, which never reloads the registry.

            :return: dict with the next action to execute
        """
        self.ensure_one()
        website = self.env.website or self.env['website'].browse(self.env.context.get('host_id'))
        website.ensure_one()

        if not self.env.user.has_group('website.group_website_designer'):
            raise AccessError(self.env._("You don't have the necessary access rights to manage website themes."))
        if not self.sudo().filtered_domain(self.env['theme.utils']._get_themes_domain()):
            raise ValueError(f"{self.name} is not a website theme")

        theme = self
        if theme.state != 'installed':
            theme.sudo().button_immediate_install()
            # The registry has been reloaded, use the records of the new one
            theme = self.env['ir.module.module'].browse(theme.id)
            website = self.env['website'].browse(website.id)

        self.env['theme.utils']._theme_apply(theme, website)

        result = website.button_go_website()
        return result

    def button_remove_theme(self):
        """Remove the current theme of the current website."""
        website = self.env.website or self.env['website'].browse(self.env.context.get('host_id'))
        self.env['theme.utils']._theme_remove(website)

    def button_refresh_theme(self):
        """
            Reload the templates of the current website's theme on the current website.

            The theme module is not upgraded: a module upgrade is what loads a new
            version of the theme, on every website using it.
        """
        website = self.env.website or self.env['website'].browse(self.env.context.get('host_id'))
        self.env['theme.utils']._theme_load(website.theme_id, website)

    @api.model
    def update_list(self):
        res = super(IrModuleModule, self).update_list()
        self.env['theme.utils']._update_theme_images()
        return res

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
