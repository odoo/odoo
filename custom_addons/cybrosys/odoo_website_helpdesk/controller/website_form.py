# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Arshad Ali Pottengal (<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
import base64
import json
from psycopg2 import IntegrityError
from odoo import http, _
from odoo.http import request
from odoo.exceptions import ValidationError
from odoo.addons.website.controllers.form import WebsiteForm


class HelpdeskProduct(http.Controller):
    """    Controller for handling helpdesk products.
    """

    @http.route('/product', auth='public', type='jsonrpc')
    def product(self):
        prols = []
        acc = request.env['product.template'].sudo().search([])
        for i in acc:
            dic = {'name': i['name'],
                   'id': i['id']}
            prols.append(dic)
        return prols


class WebsiteFormInherit(WebsiteForm):

    def _handle_website_form(self, model_name, **kwargs):
        """
        Handle the submission of website forms.
        :param model_name: The name of the model associated with the form.
        :type model_name: str
        :param kwargs: Keyword arguments containing form data.
        :type kwargs: dict
        :return: JSON response indicating the success or failure of form submission.
        :rtype: str
        """
        lowest_stage_id = None
        if model_name == 'ticket.helpdesk':
            tickets = request.env['ticket.stage'].sudo().search([])
            if tickets:
                sequence = tickets.mapped('sequence')
                lowest_sequence = tickets.filtered(
                    lambda x: x.sequence == min(sequence))
                if lowest_sequence:
                    lowest_stage_id = lowest_sequence[0]
            if lowest_stage_id is None:
                return json.dumps(
                    {'error': "No stage found with the lowest sequence."})
            products = kwargs.get('product')
            if request.env.user and request.env.user.id != request.env.ref(
                    'base.public_user').id:
                partner_create = request.env.user.partner_id
            else:
                email = kwargs.get('email_from')
                existing_partner = request.env['res.partner'].sudo().search([
                    ('email', '=', email)
                ], limit=1)
                if existing_partner:
                    partner_create = existing_partner
                else:
                    partner_create = request.env['res.partner'].sudo().create({
                        'name': kwargs.get('customer_name'),
                        'company_name': kwargs.get('company'),
                        'phone': kwargs.get('phone'),
                        'email': kwargs.get('email_from')
                    })
            if products:
                split_product = products.split(',')
                product_list = [int(i) for i in split_product]
                rec_val = {
                    'customer_name': kwargs.get('customer_name'),
                    'subject': kwargs.get('subject'),
                    'description': kwargs.get('description'),
                    'email': kwargs.get('email_from'),
                    'phone': kwargs.get('phone'),
                    'priority': kwargs.get('priority'),
                    'product_ids': product_list,
                    'stage_id': lowest_stage_id.id,
                    'customer_id': partner_create.id,
                    'ticket_type_id': kwargs.get('ticket_type_id'),
                    'category_id': kwargs.get('category'),
                }
            else:
                rec_val = {
                    'customer_name': kwargs.get('customer_name'),
                    'subject': kwargs.get('subject'),
                    'description': kwargs.get('description'),
                    'email': kwargs.get('email_from'),
                    'phone': kwargs.get('phone'),
                    'priority': kwargs.get('priority'),
                    'stage_id': lowest_stage_id.id,
                    'customer_id': partner_create.id,
                    'ticket_type_id': kwargs.get('ticket_type_id'),
                    'category_id': kwargs.get('category'),
                }

            ticket_id = request.env['ticket.helpdesk'].sudo().create(rec_val)
            request.session['ticket_number'] = ticket_id.name
            request.session['ticket_id'] = ticket_id.id
            model_record = request.env['ir.model'].sudo().search(
                [('model', '=', model_name)])
            attachments = []
            attachment_index = 0
            while f"ticket_attachment[0][{attachment_index}]" in kwargs:
                attachment_key = f"ticket_attachment[0][{attachment_index}]"
                if attachment_key in kwargs:
                    attachment = kwargs[attachment_key]
                    attachments.append(attachment)
                attachment_index += 1
            for attachment in attachments:
                attached_file = attachment.read()
                request.env['ir.attachment'].sudo().create({
                    'name': attachment.filename,
                    'res_model': 'ticket.helpdesk',
                    'res_id': ticket_id.id,
                    'type': 'binary',
                    'datas': base64.encodebytes(attached_file),
                })
            request.session['form_builder_model_model'] = model_record.model
            request.session['form_builder_model'] = model_record.name
            request.session['form_builder_id'] = ticket_id.id
            return json.dumps({'id': ticket_id.id})
        else:
            model_record = request.env['ir.model'].sudo().search(
                [('model', '=', model_name)])
            if not model_record:
                return json.dumps(
                    {'error': _("The form's specified model does not exist")})
            try:
                data = self.extract_data(model_record, request.params)
            except ValidationError as e:
                return json.dumps({'error_fields': e.args[0]})
            try:
                id_record = self.insert_record(request, model_record,
                                               data['record'], data['custom'],
                                               data.get('meta'))
                if id_record:
                    self.insert_attachment(model_record, id_record,
                                           data['attachments'])
                    if model_name == 'mail.mail':
                        request.env[model_name].sudo().browse(id_record).send()
            except IntegrityError:
                return json.dumps(False)
            request.session['form_builder_model_model'] = model_record.model
            request.session['form_builder_model'] = model_record.name
            request.session['form_builder_id'] = id_record
            return json.dumps({'id': id_record})
