# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website.controllers import form
from odoo.http import request

class WebsiteForm(form.WebsiteForm):
    def insert_record(self, request, model, values, custom, meta=None):
        if model.model == 'project.task':
            visitor_sudo = request.env['website.visitor']._get_visitor_from_request()
            visitor_partner = visitor_sudo.partner_id
            if visitor_partner:
                values['partner_id'] = visitor_partner.id

        return super().insert_record(request, model, values, custom, meta=meta)

    def insert_attachment(self, model, id_record, files):
        super().insert_attachment(model, id_record, files)
        # If the task form is submit with attachments,
        # Give access token to these attachments and make the message
        # accessible to the portal user.
        model_name = model.model
        if model_name == "project.task":
            task = model.env[model_name].browse(id_record)
            attachments = request.env['ir.attachment'].sudo().search([('res_model', '=', model_name), ('res_id', '=', task.id), ('access_token', '=', False)])
            attachments.generate_access_token()
            message_ids = task.message_ids.filtered(lambda m: m.attachment_ids == attachments)
            message_ids.is_internal = False
            message_ids.subtype_id.internal = False
