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

from odoo import models, fields, _
import http.client

from odoo.exceptions import UserError


class SendGridSendEmails(models.Model):
    _name = "email.api"
    _description = "Email Reports"

    name = fields.Char(string="Name")
    company_name = fields.Char(string="Company Name")
    recipient_name = fields.Char(string="Recipient Name")
    to_email = fields.Char(string="Recipient Email ID")
    to_email_partner = fields.Many2one("res.partner", string="Recipient Emails")
    to_email_partner_check = fields.Boolean()
    to_email_lead = fields.Many2one("crm.lead", string="Recipient Emails")
    to_email_lead_check = fields.Boolean()
    to_email_contact = fields.Many2one("mailing.contact", string="Recipient Emails")
    to_email_contact_check = fields.Boolean()
    from_email = fields.Many2one("email.sent", string="Sender Email")
    temp_type = fields.Many2one('email.template', string="Email Template")
    temp_id = fields.Char(string="Template_id")
    send_date = fields.Datetime(string="Send Date", readonly=True, default=fields.Datetime.now)
    error_msg = fields.Text(string="Error Content", readonly=True)
    error_check = fields.Boolean()
    state = fields.Selection([('send', "Send"), ('error', "Error")], readonly=True, string="State", default='send')
    bounce_msg = fields.Text(string="Bounce Message")
    email_finder = fields.Integer(string="Email finder")

    def bounce_check(self):
        """
        function is used for Checking Email Bounce
        Status.

        """

        conn = http.client.HTTPSConnection("api.sendgrid.com")

        payload = "{}"

        api_key = ""
        api_info = self.env['ir.config_parameter'].search(
            [('key', '=', "SendGrid API Key " + company_id.name + "")])
        if not api_info:
            raise UserError(_("It Needs API Key"))
        if api_info.company_id.id == self.env.company.id:
            api_key = api_info.value
        if not api_key and api_key == "":
            raise UserError(_("Your Company Needs an API Key"))
        headers = {'authorization': "Bearer " + api_key + ""}

        conn.request("GET", "/v3/suppression/bounces/" + self.to_email + "", payload, headers)

        res = conn.getresponse()
        print("res", res)
        data = res.read()
        print("data1", data)
        bounce_msg = json.loads(data.decode("utf-8"))
        if bounce_msg:
            self.bounce_msg = bounce_msg[0]['reason']

        else:
            self.bounce_msg = "This Email Is Not Bounced"

    def send_error_mails(self):
        """
        function is used for Resending Error State
        mails.

        """
        company_id = self.env.company
        api_key = ""
        for line in self:
            if line.state == 'error':
                if not line.temp_id:
                    raise UserError(_("It Needs A Template ID"))
                if line.from_email:
                    from_email = line.from_email.email_id
                else:
                    from_email = "noreply@johndoe.com"
                api_info = self.env['ir.config_parameter'].search(
                    [('key', '=', "SendGrid API Key " + company_id.name + "")])
                if not api_info:
                    raise UserError(_("It Needs API Key"))
                if api_info.company_id.id == self.env.company.id:
                    api_key = api_info.value
                if not api_key and api_key == "":
                    raise UserError(_("Your Company Needs an API Key"))
                conn = http.client.HTTPSConnection("api.sendgrid.com")
                to_company = line.company_name
                if not to_company:
                    to_company = ""
                temp_id = line.temp_id
                payload = ""
                if line.to_email and line.recipient_name:
                    payload = "{\"personalizations\":[{\"to\":[{\"email\":\"" + line.to_email + "\"}],\"dynamic_template_data\":{\"firstname\":\"" + line.recipient_name + "\",\"english\":\"true\",\"company\":\"" + to_company + "\"},\"subject\":\"Official Mail\"}],\"from\":{\"email\":\"" + from_email + "\",},\"template_id\":\"" + temp_id + "\"}"
                headers = {
                    'authorization': "Bearer " + api_key + "",
                    'content-type': "application/json"
                }

                conn.request("POST", "/v3/mail/send", payload, headers)

                res = conn.getresponse()

                data_msg = res.read()

                if data_msg.decode("utf-8"):
                    error_data = json.loads(data_msg.decode("utf-8"))
                    line.error_msg = error_data['errors'][0]['message']
                if not data_msg.decode("utf-8"):
                    line.state = 'send'
                    line.error_msg = ""
                    line.error_check = False
                    email_id_use = self.env['mailing.mailing'].search([('id', '=', line.email_finder)])
                    email_id_use.send_grid_check = True
                    email_id_use.sent_count += 1
                    email_id_use.write({
                        'state': 'done'
                    })
