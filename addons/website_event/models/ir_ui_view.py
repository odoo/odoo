# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


# Allow restricted editors to edit the pages and menus of the events they can write on, without having
# to give them designer rights, which would allow them to edit all pages and menus of the whole website.
class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    def _can_be_edited_by_event_editor(self):
        self.ensure_one()

        # No need to check if already su
        if self.env.su or not (self.env.user.has_group('event.group_event_manager') and self.env.user.has_group('website.group_website_restricted_editor')):
            return False

        IrUiViewSudo = self.sudo()

        # Views without keys are never event pages views
        page_keys = [key for key in (IrUiViewSudo | IrUiViewSudo.inherit_id).mapped('key') if key]
        if not page_keys:
            return False

        events_sudo = self.env['website.event.menu'].sudo().search([
            ('view_id.key', 'in', page_keys),
        ]).event_id

        return events_sudo and events_sudo.with_env(self.env).has_access('write')

    def save(self, value, xpath=None):
        if xpath and self._can_be_edited_by_event_editor():
            return self.sudo().with_context(website_event_page_save=True).save(value, xpath=xpath)
        return super().save(value, xpath=xpath)

    @api.model
    def save_embedded_field(self, el):

        # Embed fields should still be saved with the rights of the user
        if self.env.su and self.env.context.get('website_event_page_save'):
            return self.sudo(False).save_embedded_field(el)

        # Only a write access on the name field of a website.menu can be bypassed
        if not el.get('data-oe-id') or not (el.get('data-oe-model') == 'website.menu' and el.get('data-oe-field') == 'name'):
            return super().save_embedded_field(el)

        menu_sudo = self.env['website.menu'].sudo().browse(int(el.get('data-oe-id')))
        if menu_sudo._can_be_edited_by_event_editor():
            return super(IrUiView, self.sudo()).save_embedded_field(el)
        return super().save_embedded_field(el)

    def _update_field_translations(self, field_name, translations, digest=None, source_lang=''):

        if field_name == 'arch_db' and self._can_be_edited_by_event_editor():
            IrUiViewSudo = self.sudo()
            return IrUiViewSudo._update_field_translations(field_name, translations, digest=digest, source_lang=source_lang)

        return super()._update_field_translations(field_name, translations, digest=digest, source_lang=source_lang)
