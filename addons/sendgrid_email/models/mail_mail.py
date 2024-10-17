# -*- coding: utf-8 -*-
###################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2019-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#    Author: Noushid Khan.P (<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################

import json

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import http.client
import markupsafe
from markupsafe import escape



class SendGridEmail(models.Model):
    _inherit = 'mailing.mailing'

    email_temp = fields.Many2one("email.template", string="Email Template")
    temp_id = fields.Char(string="Template ID")
    from_email = fields.Many2one("email.sent", string="Sender Email")
    to_email_partner = fields.Many2many("res.partner", string="Recipient Emails")
    to_email_partner_check = fields.Boolean()
    to_email_lead = fields.Many2many("crm.lead", string="Recipient Emails")
    to_email_lead_check = fields.Boolean()
    to_email_contact = fields.Many2many("mailing.contact", string="Recipient Emails")
    to_email_contact_check = fields.Boolean()
    email_finder = fields.Integer(string="Email finder")
    sent_count = fields.Integer(string="Send Count")
    send_grid_check = fields.Boolean()
    temp_check = fields.Boolean()

    def action_send_grid(self):
        print("action")
        """
        function used for Sending emails using
        SendGrid API using "sendgrid" Button
        and creating report based on states.

        """
        company_id = self.env.company
        api_key = ""
        conn = http.client.HTTPSConnection("api.sendgrid.com")
        print("conn", conn)
        if not self.temp_id:
            raise UserError(_("It Needs A Template ID"))
        if self.from_email:
            from_email = self.from_email.email_id
            print("from_email", from_email)
            from_name = self.from_email.name
            print("from_name", from_name)
            print("to_email_partner", self.to_email_partner)
        else:
            from_email = "noreply@johndoe.com"
            from_name = "JohnDoe"
        if self.to_email_partner:
            print("to_email_partner")
            api_info = self.env['ir.config_parameter'].search(
                [('key', '=', "SendGrid API Key " + company_id.name + "")])
            print("api_info", api_info)
            if not api_info:
                raise UserError(_("It Needs API Key"))
            if api_info.company_id.id == self.env.company.id:
                api_key = api_info.value
            if not api_key and api_key == "":
                raise UserError(_("Your Company Needs an API Key"))
            for data in self.to_email_partner:
                to_email = data.email
                print("to_email", to_email)
                to_name = data.name
                to_company = data.company_name
                if not to_company:
                    to_company = ""
                temp_id = self.temp_id
                if to_email:
                    payload = "{\"personalizations\":[{\"to\":[{\"email\":\"" + to_email + "\"}],\"dynamic_template_data\":{\"firstname\":\"" + to_name + "\",\"english\":\"true\",\"company\":\"" + to_company + "\"},\"subject\":\"Official Mail\"}],\"from\":{\"email\":\"" + from_email + "\",\"name\":\"" + from_name + "\"},\"template_id\":\"" + temp_id + "\"}"

                headers = {
                    'authorization': "Bearer " + api_key + "",
                    'content-type': "application/json"
                }

                conn.request("POST", "/v3/mail/send", payload, headers)

                res = conn.getresponse()
                data_msg = res.read()
                error_msg = ''
                if data_msg.decode("utf-8"):
                    error_data = json.loads(data_msg.decode("utf-8"))
                    error_msg = error_data['errors'][0]['message']
                if not data_msg.decode("utf-8"):
                    self.sent_count += 1
                    self.write({
                        'state': 'done'
                    })
                    self.env['email.api'].create({
                        'name': self.subject,
                        'to_email_partner': data.id,
                        'to_email': to_email,
                        'recipient_name': to_name,
                        'company_name': to_company,
                        'from_email': self.from_email.id,
                        'temp_type': self.email_temp.id,
                        'temp_id': self.temp_id,
                        'to_email_partner_check': True,
                        'email_finder': self.id
                    })

                elif error_msg:
                    self.env['email.api'].create({
                        'name': self.subject,
                        'to_email_partner': data.id,
                        'to_email': to_email,
                        'recipient_name': to_name,
                        'company_name': to_company,
                        'from_email': self.from_email.id,
                        'temp_type': self.email_temp.id,
                        'temp_id': self.temp_id,
                        'error_msg': error_msg,
                        'state': 'error',
                        'to_email_partner_check': True,
                        'error_check': True,
                        'email_finder': self.id
                    })
            self.email_finder = self.id
            self.send_grid_check = True
        elif self.to_email_lead:
            api_info = self.env['ir.config_parameter'].search(
                [('key', '=', "SendGrid API Key " + company_id.name + "")])
            if not api_info:
                raise UserError(_("It Needs API Key"))
            if api_info.company_id.id == self.env.company.id:
                api_key = api_info.value
            if not api_key and api_key == "":
                raise UserError(_("Your Company Needs an API Key"))
            for data in self.to_email_lead:
                to_email = data.email_from
                to_name = data.contact_name
                if not to_name:
                    raise UserError(_("Your Lead Needs A Contact Name"))
                to_company = data.partner_name
                if not to_company:
                    to_company = ""
                temp_id = self.temp_id
                payload = ""
                if to_email:
                    payload = "{\"personalizations\":[{\"to\":[{\"email\":\"" + to_email + "\"}],\"dynamic_template_data\":{\"firstname\":\"" + to_name + "\",\"english\":\"true\",\"company\":\"" + to_company + "\"},\"subject\":\"Official Mail\"}],\"from\":{\"email\":\"" + from_email + "\",\"name\":\"" + from_name + "\"},\"template_id\":\"" + temp_id + "\"}"

                headers = {
                    'authorization': "Bearer " + api_key + "",
                    'content-type': "application/json"
                }

                conn.request("POST", "/v3/mail/send", payload, headers)

                res = conn.getresponse()
                data_msg = res.read()

                error_msg = ''
                if data_msg.decode("utf-8"):
                    error_data = json.loads(data_msg.decode("utf-8"))
                    error_msg = error_data['errors'][0]['message']
                if not data_msg.decode("utf-8"):
                    self.sent_count += 1
                    self.write({
                        'state': 'done'
                    })
                    self.env['email.api'].create({
                        'name': self.subject,
                        'to_email_lead': data.id,
                        'to_email': to_email,
                        'recipient_name': to_name,
                        'company_name': to_company,
                        'from_email': self.from_email.id,
                        'temp_type': self.email_temp.id,
                        'temp_id': self.temp_id,
                        'to_email_lead_check': True,
                        'email_finder': self.id
                    })

                elif error_msg:
                    self.env['email.api'].create({
                        'name': self.subject,
                        'to_email_lead': data.id,
                        'to_email': to_email,
                        'recipient_name': to_name,
                        'company_name': to_company,
                        'from_email': self.from_email.id,
                        'temp_type': self.email_temp.id,
                        'temp_id': self.temp_id,
                        'error_msg': error_msg,
                        'state': 'error',
                        'to_email_lead_check': True,
                        'error_check': True,
                        'email_finder': self.id
                    })
            self.email_finder = self.id
            self.send_grid_check = True
        elif self.to_email_contact:
            api_info = self.env['ir.config_parameter'].search(
                [('key', '=', "SendGrid API Key " + company_id.name + "")])
            if not api_info:
                raise UserError(_("It Needs API Key"))
            if api_info.company_id.id == self.env.company.id:
                api_key = api_info.value
            if not api_key and api_key == "":
                raise UserError(_("Your Company Needs an API Key"))
            for data in self.to_email_contact:
                to_email = data.email
                to_name = data.name
                to_company = data.company_name
                if not to_company:
                    to_company = ""
                temp_id = self.temp_id
                payload = ""
                if to_email:
                    payload = "{\"personalizations\":[{\"to\":[{\"email\":\"" + to_email + "\"}],\"dynamic_template_data\":{\"firstname\":\"" + to_name + "\",\"english\":\"true\",\"company\":\"" + to_company + "\"},\"subject\":\"Official Mail\"}],\"from\":{\"email\":\"" + from_email + "\",\"name\":\"" + from_name + "\"},\"template_id\":\"" + temp_id + "\"}"

                headers = {
                    'authorization': "Bearer " + api_key + "",
                    'content-type': "application/json"
                }

                conn.request("POST", "/v3/mail/send", payload, headers)

                res = conn.getresponse()
                data_msg = res.read()

                error_msg = ''
                if data_msg.decode("utf-8"):
                    error_data = json.loads(data_msg.decode("utf-8"))
                    error_msg = error_data['errors'][0]['message']
                if not data_msg.decode("utf-8"):
                    self.sent_count += 1
                    self.write({
                        'state': 'done'
                    })
                    self.env['email.api'].create({
                        'name': self.subject,
                        'to_email_contact': data.id,
                        'to_email': to_email,
                        'recipient_name': to_name,
                        'company_name': to_company,
                        'from_email': self.from_email.id,
                        'temp_type': self.email_temp.id,
                        'temp_id': self.temp_id,
                        'to_email_contact_check': True,
                        'email_finder': self.id
                    })

                elif error_msg:
                    self.env['email.api'].create({
                        'name': self.subject,
                        'to_email_contact': data.id,
                        'to_email': to_email,
                        'recipient_name': to_name,
                        'company_name': to_company,
                        'from_email': self.from_email.id,
                        'temp_type': self.email_temp.id,
                        'temp_id': self.temp_id,
                        'error_msg': error_msg,
                        'state': 'error',
                        'to_email_contact_check': True,
                        'error_check': True,
                        'email_finder': self.id
                    })
            self.email_finder = self.id
            self.send_grid_check = True

    @api.onchange('email_temp', 'mailing_model_id', 'contact_list_ids')
    def temp_details(self):

        """
        function used for filling subject and recipients emails
        based on template and recipient emails

        """
        if self.email_temp:
            self.temp_check = True
            self.subject = self.email_temp.ver_subject
            print("subject", type(self.subject))
            self.temp_id = self.email_temp.temp_id
            print("temp_id", type(self.temp_id))
            self.body_html = str(self.email_temp.temp_cont)
            print("body_html", self.body_html)
            print("body_html", type(self.body_html))
            self.body_arch = self.email_temp.temp_cont
            self.body_arch = "str(self.email_temp.temp_cont)"
            print("body_arch", self.body_arch)
            print("body_arch", type(self.body_arch))
        else:
            self.temp_check = False

        # if self.mailing_model_real == "sale.order" or self.mailing_model_real == "event.registration" or self.mailing_model_real == "event.track":
        #     self.to_email_contact = False
        #     self.to_email_lead = False
        #     self.mailing_domain = "[]"
        #     for mass_mailing in self:
        #         mai_data = mass_mailing.sudo()._get_recipients()
        #         email_ids = self.env[self.mailing_model_real].search([('id', '=', mai_data)])
        #         if email_ids:
        #             self.to_email_partner = email_ids.partner_id
        if self.mailing_model_real == "crm.lead":
            self.to_email_contact = False
            self.to_email_partner = False
            self.mailing_domain = "[]"
            for mass_mailing in self:
                mai_data = mass_mailing.sudo()._get_recipients()
                email_ids = self.env[self.mailing_model_real].search([('id', '=', mai_data)])
                if email_ids:
                    self.to_email_lead = email_ids
        elif self.mailing_model_real == "mailing.contact":
            self.to_email_partner = False
            self.to_email_lead = False
            self.mailing_domain = "[]"
            for mass_mailing in self:
                mai_data = mass_mailing.sudo()._get_recipients()
                email_ids = self.env[self.mailing_model_real].search([('id', '=', mai_data)])
                if email_ids:
                    self.to_email_contact = email_ids
            if self.contact_list_ids:
                email_ids = self.env[self.mailing_model_real].search(
                    [('id', '=', mai_data), ('list_ids', '=', self.contact_list_ids.ids)])
                self.to_email_contact = email_ids

        else:
            self.to_email_contact = False
            self.to_email_lead = False
            self.mailing_domain = "[]"
            for mass_mailing in self:
                mai_data = mass_mailing.sudo()._get_recipients()
                email_ids = self.env[self.mailing_model_real].search([('id', '=', mai_data)])
                if email_ids:
                    self.to_email_partner = email_ids

    @api.onchange('mailing_domain')
    def get_mails_recipients(self):
        """
        function used for filtering based on domain
        filter

        """
        # if self.mailing_model_real == "sale.order" or self.mailing_model_real == "event.registration" or self.mailing_model_real == "event.track":
        #     for mass_mailing in self:
        #         mai_data = mass_mailing.sudo()._get_recipients()
        #         email_ids = self.env[self.mailing_model_real].search([('id', '=', mai_data)])
        #         if email_ids:
        #             self.to_email_partner = email_ids.partner_id
        if self.mailing_model_real == "crm.lead":
            for mass_mailing in self:
                mai_data = mass_mailing.sudo()._get_recipients()
                email_ids = self.env[self.mailing_model_real].search([('id', '=', mai_data)])
                if email_ids:
                    self.to_email_lead = email_ids
        elif self.mailing_model_real == "mailing.contact":
            for mass_mailing in self:
                mai_data = mass_mailing.sudo()._get_recipients()
                email_ids = self.env[self.mailing_model_real].search([('id', '=', mai_data)])
                if email_ids:
                    self.to_email_contact = email_ids
        else:
            for mass_mailing in self:
                mai_data = mass_mailing.sudo()._get_recipients()
                email_ids = self.env[self.mailing_model_real].search([('id', '=', mai_data)])
                if email_ids:
                    self.to_email_partner = email_ids

    @api.onchange('to_email_partner', 'to_email_lead', 'to_email_contact')
    def show_hide_fields(self):
        """
        function is used for Enabling Needed
        recipient mail fields by changing check box
        values.

        """
        if self.to_email_partner:
            self.to_email_partner_check = True
        else:
            self.to_email_partner_check = False
        if self.to_email_lead:
            self.to_email_lead_check = True
        else:
            self.to_email_lead_check = False
        if self.to_email_contact:
            self.to_email_contact_check = True
        else:
            self.to_email_contact_check = False

    def _action_view_documents_filtered(self, view_filter):
        """
        function is used for returning send view in
        needed recipient tree view

        """
        if view_filter == 'sent' and self.temp_id:
            res_ids = []
            for mass_mailing in self:
                mai_data = mass_mailing.sudo()._get_recipients()
                res_ids = self.env[self.mailing_model_real].search([('id', '=', mai_data)])
            model_name = self.env['ir.model']._get(self.mailing_model_real).display_name
            return {
                'name': model_name,
                'type': 'ir.actions.act_window',
                'view_mode': 'tree',
                'res_model': self.mailing_model_real,
                'domain': [('id', 'in', res_ids.ids)],
                'context': dict(self._context, create=False)
            }
        else:
            return super(SendGridEmail, self)._action_view_documents_filtered(view_filter)

    def _compute_statistics(self):
        """
        function is used for computing Send mails Smart button
        count

        """
        self.env.cr.execute("""
                   SELECT
                       m.id as mailing_id,
                       COUNT(s.id) AS expected,
                       COUNT(s.sent_datetime) AS sent,
                       COUNT(s.trace_status) FILTER (WHERE s.trace_status = 'outgoing') AS scheduled,
                       COUNT(s.trace_status) FILTER (WHERE s.trace_status = 'cancel') AS canceled,
                       COUNT(s.trace_status) FILTER (WHERE s.trace_status in ('sent', 'open', 'reply')) AS delivered,
                       COUNT(s.trace_status) FILTER (WHERE s.trace_status in ('open', 'reply')) AS opened,
                       COUNT(s.links_click_datetime) AS clicked,
                       COUNT(s.trace_status) FILTER (WHERE s.trace_status = 'reply') AS replied,
                       COUNT(s.trace_status) FILTER (WHERE s.trace_status = 'bounce') AS bounced,
                       COUNT(s.trace_status) FILTER (WHERE s.trace_status = 'error') AS failed
                   FROM
                       mailing_trace s
                   RIGHT JOIN
                       mailing_mailing m
                       ON (m.id = s.mass_mailing_id)
                   WHERE
                       m.id IN %s
                   GROUP BY
                       m.id
               """, (tuple(self.ids),))
        for row in self.env.cr.dictfetchall():
            total = (row['expected'] - row['canceled']) or 1
            row['received_ratio'] = 100.0 * row['delivered'] / total
            row['opened_ratio'] = 100.0 * row['opened'] / total
            row['replied_ratio'] = 100.0 * row['replied'] / total
            row['bounced_ratio'] = 100.0 * row['bounced'] / total
            row['clicks_ratio'] = 100.0 * row['clicked'] / total
            self.browse(row.pop('mailing_id')).update(row)
        for mail in self:
            if mail.temp_id:
                mail.sent = mail.sent_count
            else:
                return super(SendGridEmail, self)._compute_statistics()