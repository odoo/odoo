# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo import _
from odoo.addons.base.models.ir_qweb_fields import nl2br_enclose
from odoo.tools import html2plaintext
from odoo.addons.website.controllers import form


class WebsiteForm(form.WebsiteForm):
    def _is_project_task_model(self, model_name):
        return model_name == 'project.task'

    def _get_default_field_data(self, model_name, values, default_field):
        res = super()._get_default_field_data(model_name, values, default_field)
        if self._is_project_task_model(model_name):
            return nl2br_enclose(default_field.name.capitalize(), 'h4') + nl2br_enclose(html2plaintext(res), 'p')
        return res

    def _get_custom_label(self, model_name, _custom_label, custom):
        res = super()._get_custom_label(model_name, _custom_label, custom)
        if self._is_project_task_model(model_name):
            return nl2br_enclose(_("Other Information"), 'h4') + res if res else ''
        return res

    def _update_values(self, model_name, values):
        if self._is_project_task_model(model_name):
            # When a task is created from the web editor, if the key 'user_ids' is not present, the user_ids is filled with the odoo bot. We set it to False to ensure it is not.
            values.setdefault('user_ids', False)

    def _update_custom(self, model_name, custom):
        if self._is_project_task_model(model_name) and custom:
            custom.replace('email_from', 'Email')

    def extract_data(self, model, values):
        data = super().extract_data(model, values)
        if self._is_project_task_model(model.model) and values.get('email_from'):
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
