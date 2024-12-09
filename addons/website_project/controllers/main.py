# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.base.models.ir_qweb_fields import nl2br_enclose
from odoo.addons.website.controllers import form


class WebsiteForm(form.WebsiteForm):
    def insert_record(self, request, model_sudo, values, custom, meta=None):
        model_name = model_sudo.model
        if model_name == 'project.task':
            # When a task is created from the web editor, if the key 'user_ids' is not present, the user_ids is filled with the odoo bot. We set it to False to ensure it is not.
            values.setdefault('user_ids', False)
            if custom:
                custom.replace('email_from', 'Email')

        res = super().insert_record(request, model_sudo, values, custom, meta=meta)
        if model_name != 'project.task':
            return res
        task = request.env['project.task'].sudo().browse(res)
        default_field = model_sudo.website_form_default_field_id
        if default_field.name and task[default_field.name]:
            task._message_log(
                body=nl2br_enclose(task[default_field.name], 'p'),
                message_type='comment',
            )
        return res

    def extract_data(self, model_sudo, values):
        data = super().extract_data(model_sudo, values)
        if model_sudo.model == 'project.task' and values.get('email_from'):
            partners_list = request.env['mail.thread'].sudo()._mail_find_partner_from_emails([values['email_from']])
            partner = partners_list[0] if partners_list else self.env['res.partner']
            data['record']['partner_id'] = partner.id
            data['record']['email_from'] = values['email_from']
            if partner:
                if not partner.phone and values.get('partner_phone'):
                    data['record']['partner_phone'] = values['partner_phone']
                if not partner.name:
                    data['record']['partner_name'] = values['partner_name']
                if not partner.company_name and values.get('partner_company_name'):
                    data['record']['partner_company_name'] = values['partner_company_name']
            else:
                data['record']['email_cc'] = values['email_from']
                if values.get('partner_phone'):
                    data['record']['partner_phone'] = values['partner_phone']
                data['record']['partner_name'] = values['partner_name']
                if values.get('partner_company_name'):
                    data['record']['partner_company_name'] = values['partner_company_name']
        return data
