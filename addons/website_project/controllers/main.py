# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.base.models.ir_qweb_fields import nl2br_enclose
from odoo.addons.website.controllers import form


class WebsiteForm(form.WebsiteForm):
    def insert_record(self, request, model, values, custom, meta=None):
        if model.model == 'project.task':
            # When a task is created from the web editor, if the key 'user_ids' is not present, the user_ids is filled with the odoo bot. We set it to False to ensure it is not.
            values.setdefault('user_ids', False)
            if custom:
                custom.replace('email_from', 'Email')

        res = super().insert_record(request, model, values, custom, meta=meta)
        if model.model != 'project.task':
            return res
        task = request.env['project.task'].sudo().browse(res)
        default_field = model.website_form_default_field_id
        if default_field.name and task[default_field.name]:
            task._message_log(
                body=nl2br_enclose(task[default_field.name], 'p'),
                message_type='comment',
            )
        return res

    def extract_data(self, model, values):
        data = super().extract_data(model, values)
        if model.model == 'project.task' and values.get('email_from'):
            partners_list = request.env['mail.thread'].sudo()._mail_find_partner_from_emails([values['email_from']])
            partner_id = partners_list[0].id if partners_list else False
            data['record']['partner_id'] = partner_id
            data['record']['email_from'] = values['email_from']
            if not partner_id:
                data['record']['email_cc'] = values['email_from']
        return data
