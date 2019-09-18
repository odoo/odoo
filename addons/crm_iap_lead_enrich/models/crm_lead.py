# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging

from odoo import api, fields, models, tools
from odoo.addons.iap import InsufficientCreditError

_logger = logging.getLogger(__name__)


class Lead(models.Model):
    _inherit = 'crm.lead'

    reveal_id = fields.Char(string='Reveal ID', index=True)
    iap_enrich_done = fields.Boolean(string='Enrichment done', help='Whether IAP service for lead enrichment based on email has been performed on this lead.')

    @api.model
    def _iap_enrich_leads_cron(self):
        timeDelta = fields.datetime.now() - datetime.timedelta(hours=1)
        leads = self.search([
            ('iap_enrich_done', '=', False),
            ('reveal_id', '=', False),
            ('probability', 'not in', (0, 100)),
            ('create_date', '>', timeDelta)
        ])
        leads._iap_enrich(from_cron=True)

    def _iap_enrich(self, from_cron=False):
        lead_emails = {}
        for lead in self:
            if lead.probability in (0, 100) or lead.iap_enrich_done:
                continue
            normalized_email = tools.email_normalize(lead.partner_address_email) or tools.email_normalize(lead.email_from)
            if normalized_email:
                lead_emails[lead.id] = normalized_email.split('@')[1]
            else:
                lead.message_post_with_view(
                    'crm_iap_lead_enrich.mail_message_lead_enrich_no_email',
                    subtype_id=self.env.ref('mail.mt_note').id)

        if lead_emails:
            try:
                iap_response = self.env['iap.enrich.api']._request_enrich(lead_emails)
            except InsufficientCreditError:
                _logger.info('Sent batch %s enrich requests: failed because of credit', len(lead_emails))
                self._iap_enrich_notify_no_more_credit()
                if not from_cron:
                    data = {
                        'url': self.env['iap.account'].get_credits_url('reveal'),
                    }
                    self[0].message_post_with_view(
                        'crm_iap_lead_enrich.mail_message_lead_enrich_no_credit',
                        values=data,
                        subtype_id=self.env.ref('mail.mt_note').id)
            except Exception as e:
                _logger.info('Sent batch %s enrich requests: failed with exception %s', len(lead_emails), e)
            else:
                _logger.info('Sent batch %s enrich requests: success', len(lead_emails))
                self._iap_enrich_from_response(iap_response)
                self.env['ir.config_parameter'].sudo().set_param('crm_iap_lead_enrich.credit_notification', False)

    @api.model
    def _iap_enrich_from_response(self, iap_response):
        """ Handle from the service and enrich the lead accordingly

        :param iap_response: dict{lead_id: company data or False}
        """
        for lead in self.search([('id', 'in', list(iap_response.keys()))]):  # handle unlinked data by performing a search
            iap_data = iap_response.get(str(lead.id))
            if not iap_data:
                lead.message_post_with_view('crm_iap_lead_enrich.mail_message_lead_enrich_notfound', subtype_id=self.env.ref('mail.mt_note').id)
                continue

            values = {'iap_enrich_done': True}
            lead_fields = ['description', 'partner_name', 'reveal_id', 'street', 'city', 'zip']
            iap_fields = ['description', 'name', 'clearbit_id', 'location', 'city', 'postal_code']
            for lead_field, iap_field in zip(lead_fields, iap_fields):
                if not lead[lead_field] and iap_data.get(iap_field):
                    values[lead_field] = iap_data[iap_field]

            if not lead.phone and iap_data.get('phone_numbers'):
                values['phone'] = iap_data['phone_numbers'][0]
            if not lead.mobile and iap_data.get('phone_numbers') and len(iap_data['phone_numbers']) > 1:
                values['mobile'] = iap_data['phone_numbers'][1]
            if not lead.country_id and iap_data.get('country_code'):
                country = self.env['res.country'].search([('code', '=', iap_data['country_code'].upper())])
                values['country_id'] = country.id
            else:
                country = lead.country_id
            if not lead.state_id and country and iap_data.get('state_code'):
                state = self.env['res.country.state'].search([
                    ('code', '=', iap_data['state_code']),
                    ('country_id', '=', country.id)
                ])
                values['state_id'] = state.id

            lead.write(values)
            lead.message_post_with_view(
                'crm_iap_lead_enrich.mail_message_lead_enrich_with_data',
                values=lead._iap_enrich_get_message_data(iap_data),
                subtype_id=self.env.ref('mail.mt_note').id
            )

    def _iap_enrich_get_message_data(self, company_data):
        log_data = {
            'twitter': company_data.get('twitter'),
            'logo': company_data.get('logo'),
            'phone_numbers': company_data.get('phone_numbers'),
            'facebook': company_data.get('facebook'),
            'linkedin': company_data.get('linkedin'),
            'crunchbase': company_data.get('crunchbase'),
            'tech': [t.replace('_', ' ').title() for t in company_data.get('tech', [])],
        }
        timezone = company_data.get('timezone')
        if timezone:
            log_data.update({
                'timezone': timezone.replace('_', ' ').title(),
                'timezone_url': company_data.get('timezone_url'),
            })
        return log_data

    @api.model
    def _iap_enrich_notify_no_more_credit(self):
        """ Notify when user has no credits anymore. In order to avoid to spam
        people each hour, an ir.config_parameter is set. """
        already_notified = self.env['ir.config_parameter'].sudo().get_param('crm_iap_lead_enrich.credit_notification')
        if already_notified == 'True':
            return

        iap_account = self.env['iap.account'].search([('service_name', '=', 'reveal')], limit=1)
        if not iap_account:
            return

        mail_template = self.env.ref('crm_iap_lead_enrich.mail_template_data_iap_lead_enrich_nocredit')
        if not mail_template:
            return

        mail_template.sudo().send_mail(iap_account.id, force_send=False, notif_layout='mail.mail_notification_light')
        self.env['ir.config_parameter'].sudo().set_param('lead_enrich.already_notified', True)
