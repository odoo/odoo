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
