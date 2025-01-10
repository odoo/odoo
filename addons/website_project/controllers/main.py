# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website.controllers import form

from odoo import _
from odoo.addons.base.models.ir_qweb_fields import nl2br_enclose
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
        if not (custom or meta) or model.model != 'project.task':
            return res
        task = request.env['project.task'].sudo().browse(res)
        custom = "<b>" + custom.replace('email_from', _('Email')).replace(' :', ':</b>').replace('\n', '\n<b>').replace('\r\n<b>', '\r\n')
        custom_label = "<h4>%s</h4>\n\n" % _("Other Information")  # Title for custom fields
        default_field = model.website_form_default_field_id
        default_field_data = values.get(default_field.name, '')
        default_field_content = "<h4>%s</h4>\n<p>%s</p>" % (default_field.name.capitalize(), html2plaintext(default_field_data))
        custom_content = (f"{default_field_content} \n\n\n" if default_field_data else '') \
                        + (f"{custom_label} {custom} \n\n " if custom else '') \
                        + (self._meta_label + meta if meta else '')

        if default_field.name:
            task._message_log(
                body=nl2br_enclose(custom_content, 'p'),
                message_type='comment',
            )
        return res
