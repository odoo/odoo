# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import _, SUPERUSER_ID
from odoo.addons.website.controllers import form
from odoo.http import request


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
        task = request.env['project.task'].browse(res)
        authenticate_message = False
        if request.session.uid:
            user_email = request.env.user.email
            form_email = values.get('email_from')
            if user_email != form_email:
                authenticate_message = _("This Task was submitted by %(user_name)s (%(user_email)s) on behalf of %(form_email)s",
                    user_name=request.env.user.name, user_email=user_email, form_email=form_email)
        else:
            authenticate_message = _("⚠️ EXTERNAL SUBMISSION - Customer not verified")
        if authenticate_message:
            task.with_user(SUPERUSER_ID)._message_log(
                body=Markup('<div class="alert alert-info" role="alert">{message}</div>').format(message=authenticate_message),
                message_type='notification',
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
