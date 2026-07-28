# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import UserError


class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    def _get_manifest(self, module_name=None):
        module_name = module_name or self.name
        return super()._get_manifest(module_name) or self._get_module_manifest(module_name)

    def _import_module_post_process(self):
        res = super()._import_module_post_process()
        self.update_theme_images()
        return res

    def _theme_upgrade_themes(self):
        imported_themes = self.filtered('imported')
        super(IrModuleModule, self - imported_themes)._theme_upgrade_themes()
        for imported_theme in imported_themes:
            for website in imported_theme._theme_get_websites_to_load():
                imported_theme._theme_load(website)

    @api.model
    def _theme_remove(self, website):
        old_themes = self.browse()
        if website.theme_id:
            old_themes = website.theme_id._theme_get_stream_themes()
        super()._theme_remove(website)
        if old_themes:
            old_themes.filtered(
                lambda t: t.imported and not t._theme_get_stream_website_ids()
            ).sudo().button_immediate_uninstall()

    def module_uninstall(self):
        if (used_imported_themes := self.filtered(
            lambda m: m.imported and m._theme_get_stream_website_ids()
        )):
            raise UserError(self.env._(
                "The following imported theme(s) are still in use on a website and cannot be"
                " uninstalled: %(themes)s. Please select a different theme on the website(s)"
                " using them first.",
                themes=", ".join(used_imported_themes.mapped('name')),
            ))
        return super().module_uninstall()
