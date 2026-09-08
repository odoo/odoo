from lxml import html
import markupsafe
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.tools import html_sanitize


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    technical_usage = fields.Selection(selection_add=[("mass_mailing", "Mass Mailing Technical")])

    def _can_edit_view(self):
        return self.env.su or self.env.user.has_group('base.group_sanitize_override')

    @api.model_create_multi
    def create(self, vals_list):
        if not self._can_edit_view():
            raise AccessError(_("You are not allowed to create views."))
        return super().create(vals_list)

    def write(self, vals):
        if not self._can_edit_view():
            raise AccessError(_("You are not allowed to modify views."))
        return super().write(vals)

    def unlink(self):
        if not self._can_edit_view():
            raise AccessError(_("You are not allowed to delete views."))
        return super().unlink()

    @api.model
    def save_snippet(self, name, arch, template_key, snippet_key, thumbnail_url, technical_usage=False):
        if self._can_edit_view():
            return super().save_snippet(name, arch, template_key, snippet_key, thumbnail_url, technical_usage)

        if technical_usage != 'mass_mailing' or template_key != 'mass_mailing.email_designer_snippets':
            raise AccessError(_("You are not allowed to save snippets in this template."))

        self._assert_static_snippet_arch(arch)
        snippet_key = re.sub(r'[^A-Za-z0-9_-]', '', snippet_key or '') or 'snippet'
        thumbnail_url = markupsafe.escape(thumbnail_url)
        arch = html_sanitize(arch, sanitize_tags=False)

        return super(IrUiView, self.sudo()).save_snippet(name, arch, template_key, snippet_key, thumbnail_url, technical_usage)

    @api.model
    def rename_snippet(self, name, view_id, template_key):
        return super(IrUiView, self._as_mass_mailing_snippet_editor(view_id)).rename_snippet(name, view_id, template_key)

    @api.model
    def delete_snippet(self, view_id, template_key):
        return super(IrUiView, self._as_mass_mailing_snippet_editor(view_id)).delete_snippet(view_id, template_key)

    def _as_mass_mailing_snippet_editor(self, view_id):
        if self._can_edit_view():
            return self

        view = self.browse(view_id)
        if view.technical_usage == 'mass_mailing' and not view.inherit_id:
            return self.sudo()
        return self

    @api.model
    def mail_allowed_qweb_expressions(self):
        return ()

    @api.model
    def _assert_static_snippet_arch(self, arch):
        if not arch:
            return
        node = html.fragment_fromstring(str(arch), create_parent='div')
        try:
            self.env['ir.qweb'].with_context(raise_on_forbidden_code_for_model='ir.ui.view')._generate_code(node)
        except PermissionError:
            raise AccessError(_("You are not allowed to save snippets containing dynamic code."))
