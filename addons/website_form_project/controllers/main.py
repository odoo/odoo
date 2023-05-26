# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website.controllers import form


class WebsiteForm(form.WebsiteForm):
    def insert_record(self, request, model, values, custom, meta=None):
        if model.model == 'project.task':
            visitor_sudo = request.env['website.visitor']._get_visitor_from_request()
            visitor_partner = visitor_sudo.partner_id
            if visitor_partner:
                values['partner_id'] = visitor_partner.id
            # When a task is created from the web editor, if the key 'user_ids' is not present, the user_ids is filled with the odoo bot. We set it to False to ensure it is not.
            values.setdefault('user_ids', False)

        return super().insert_record(request, model, values, custom, meta=meta)
