# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, Command
from odoo.addons.website.controllers.form import WebsiteForm
from odoo.http import request
from odoo.tools import email_normalize


class WebsiteNewsletterForm(WebsiteForm):

    def _handle_website_form(self, model_name, **kwargs):
        if model_name == 'mailing.contact':
            list_ids = kwargs.get('list_ids')
            if not list_ids:
                return json.dumps({'error': _('Mailing List(s) not found!')})
            list_ids = [int(x) for x in list_ids.split(',')]
            private_list_ids = request.env['mailing.list'].sudo().search([
                ('id', 'in', list_ids), ('is_public', '=', False)])
            if private_list_ids:
                return json.dumps({
                    'error': _('You cannot subscribe to the following list anymore : %s',
                               ', '.join(private_list_ids.mapped('name')))
                })
        return super()._handle_website_form(model_name, **kwargs)

    def insert_record(self, request, model_sudo, values, custom, meta=None):
        model_name = model_sudo.model
        partner = request.env.user.partner_id
        list_ids = values.get('list_ids')
        if (
            model_name != 'mailing.contact'
            or request.env.user.is_public
            or not list_ids or list_ids[0][0] != Command.SET
            or not (email := values.get('email'))
            or email_normalize(email, strict=False) != partner.email_normalized
        ):
            return super().insert_record(request, model_sudo, values, custom, meta=meta)
        list_ids = list_ids[0][2]
        contacts = request.env["mailing.list"].browse(list_ids).sudo()._update_subscription_from_email(
            partner.email_normalized, opt_out=False)
        if not contacts:
            values['partner_id'] = partner.id
            return super().insert_record(request, model_sudo, values, custom, meta=meta)
        contact = contacts[:1]
        if not contact.partner_id:
            contact.partner_id = partner
        return contact.id
