# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, Command
from odoo.http import request
from odoo.addons.website.controllers.form import WebsiteForm


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

    def insert_record(self, request, model, values, custom, meta=None):
        list_ids = values.get('list_ids')
        if (
            model.model == 'mailing.contact'
            and list_ids
            and list_ids[0][0] == Command.SET
        ):
            # The `mailing.subscription` model uses the same table as `list_ids`.
            # Creating the relation through `list_ids` bypasses that model and
            # leaves its automatic fields, notably `create_date`, empty.
            values['subscription_ids'] = [
                Command.create({'list_id': list_id})
                for list_id in values.pop('list_ids')[0][2]
            ]
        return super().insert_record(request, model, values, custom, meta=meta)
