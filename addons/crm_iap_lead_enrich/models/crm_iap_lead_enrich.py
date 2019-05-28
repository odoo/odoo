# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.addons.iap import jsonrpc,InsufficientCreditError

class Lead(models.Model):
    _inherit = 'crm.lead'

    enriched_lead = fields.Boolean(string='Lead enriched based on email')

    @api.model
    def _lead_enrich_mail(self, cron=False):
        domains = {}
        for record in self:
            if record.probability == 0:
                continue
            email_domain = record.partner_address_email or record.email_from
            if email_domain:
                domains[record.id] = email_domain.split('@')[1]
            else:
                record.message_post_with_view('crm_iap_lead_enrich.mail_message_lead_enrich_no_email', subtype_id=self.env.ref('mail.mt_note').id)        
        if domains:
            try:
                response_clearbit = self.env['crm_iap_lead_enrich.api']._make_request(domains)
                self._enrich_leads_from_response(response_clearbit)
                self.env['ir.config_parameter'].sudo().set_param('lead_enrich.already_notified', False)

            except InsufficientCreditError:
                self.notify_no_more_credit('reveal', self._name, 'lead_enrich.already_notified')
                if cron:
                    return
                data = {
                    'url' : self.env['iap.account'].get_credits_url('reveal'),
                }
                self.message_post_with_view('crm_iap_lead_enrich.mail_message_lead_enrich_no_credit', values=data, subtype_id=self.env.ref('mail.mt_note').id)

    @api.model
    def _enrich_with_cron(self):
        timeDelta = fields.datetime.now() - datetime.timedelta(hours=1)
        leads = self.search([('enriched_lead', '=', False),('reveal_id', '=', False),('probability','!=','0'),('probability','!=','100'),('create_date','>',timeDelta)])
        leads._lead_enrich_mail(True)

    @api.model
    def _create_message_data(self, record, company_data):
        log_data = {
            'lead': record,
            'twitter': company_data['twitter'],
            'logo': company_data['logo'],
            'phone_numbers': company_data['phone_numbers'],
            'facebook': company_data['facebook'],
            'linkedin': company_data['linkedin'],
            'crunchbase': company_data['crunchbase'],
            'tech': [t.replace('_', ' ').title() for t in company_data['tech']],
        }
        timezone = company_data['timezone']
        if timezone:
            log_data.update({
                'timezone': timezone.replace('_', ' ').title(),
                'timezone_url': company_data['timezone_url'],
            })
        return log_data

    @api.model
    def _enrich_leads_from_response(self, data_clearbit):
        """ This method will get the response from the service and enrich the lead accordingly """
        for lead_id, data in data_clearbit.items():
            record = self.browse(int(lead_id))
            if record.exists():
                if data:
                    street = False
                    zip_code = False
                    city = False
                    country_id = False
                    state_id = False

                    if not(record.street or record.street2 or record.zip or record.city or record.state_id or record.country_id):
                        street = data["location"]
                        zip_code = data["postal_code"]
                        city = data["city"]
                        country = record.env['res.country'].search([('code', '=', data["country_code"])])
                        if country:
                            country_id = country.id
                            state = record.env['res.country.state'].search([('code', '=', data["state_code"]),('country_id', '=', country_id)])
                            if state:
                                state_id = state.id
                    record.write({
                        'description': record.description or data['description'],
                        'partner_name': record.partner_name or data['name'],
                        'reveal_id': record.reveal_id or data['clearbit_id'],
                        'website': record.website or ('https://www.%s' % data['domain'] if data['domain'] else False),
                        'phone': record.phone or (data["phone_numbers"][0] if (len(data["phone_numbers"])>0) else False),
                        'mobile': record.mobile or (data["phone_numbers"][1] if (len(data["phone_numbers"])>1) else False),
                        'street': record.street or street,
                        'city': record.city or city,
                        'zip': record.zip or zip_code,
                        'country_id': record.country_id.id or country_id,
                        'state_id': record.state_id.id or state_id,
                        'enriched_lead': True,
                    })
                    message_values = self._create_message_data(record, data)
                    record.message_post_with_view('crm_iap_lead_enrich.mail_message_lead_enrich_with_data', values=message_values, subtype_id=self.env.ref('mail.mt_note').id)
                else:
                    record.message_post_with_view('crm_iap_lead_enrich.mail_message_lead_enrich_notfound', subtype_id=self.env.ref('mail.mt_note').id)
    @api.model
    def notify_no_more_credit(self, service_name, model_name, notification_parameter):
        """
        Notify when user has no credits anymore
        In order to avoid to spam people each hour, an ir.config_parameter is set
        """
        already_notified = self.env['ir.config_parameter'].sudo().get_param(notification_parameter, False)
        if already_notified == 'True':
            return 
        mail_template = self.env.ref('crm_iap_lead_enrich.lead_enrichment_no_credits')
        iap_account = self.env['iap.account'].search([('service_name', '=', service_name)], limit=1)
        mail_template.send_mail(iap_account.id, force_send=True, notif_layout='mail.mail_notification_light')
        self.env['ir.config_parameter'].sudo().set_param(notification_parameter, True)
