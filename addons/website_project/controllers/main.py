# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.addons.base.models.ir_qweb_fields import nl2br, nl2br_enclose
from odoo.addons.website.controllers import form
from odoo.tools import html2plaintext


class WebsiteForm(form.WebsiteForm):
    def insert_record(self, request, model, values, custom, meta=None):
        if model.model == 'project.task':
            visitor_sudo = request.env['website.visitor']._get_visitor_from_request()
            visitor_partner = visitor_sudo.partner_id
            if visitor_partner:
                values['partner_id'] = visitor_partner.id
            # When a task is created from the web editor, if the key 'user_ids' is not present, the user_ids is filled with the odoo bot. We set it to False to ensure it is not.
            values.setdefault('user_ids', False)

        res = super().insert_record(request, model, values, custom, meta=meta)
        if model.model != 'project.task':
            return res
        task = request.env['project.task'].sudo().browse(res)
        custom = custom.replace('email_from', 'Email')
        custom_label = nl2br_enclose(_("Other Information"), 'h4')  # Title for custom fields
        default_field = model.website_form_default_field_id
        default_field_data = values.get(default_field.name, '')
        default_field_content = nl2br_enclose(default_field.name.capitalize(), 'h4') + nl2br_enclose(html2plaintext(default_field_data), 'p')
        custom_content = (default_field_content if default_field_data else '') \
                        + (custom_label + custom if custom else '') \
                        + (self._meta_label + meta if meta else '')

        if default_field.name:
            if default_field.ttype == 'html':
                custom_content = nl2br(custom_content)
            task[default_field.name] = custom_content
            task._message_log(
                body=custom_content,
                message_type='comment',
            )
        return res
