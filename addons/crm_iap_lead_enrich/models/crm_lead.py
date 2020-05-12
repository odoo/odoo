# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging

from odoo import _, api, fields, models, tools
from odoo.addons.iap.tools import iap_tools

_logger = logging.getLogger(__name__)


class Lead(models.Model):
    _inherit = 'crm.lead'

    iap_enrich_done = fields.Boolean(string='Enrichment done', help='Whether IAP service for lead enrichment based on email has been performed on this lead.')
    show_enrich_button = fields.Boolean(string='Allow manual enrich', compute="_compute_show_enrich_button")

    @api.depends('email_from', 'probability', 'iap_enrich_done', 'reveal_id')
    def _compute_show_enrich_button(self):
        config = self.env['ir.config_parameter'].sudo().get_param('crm.iap.lead.enrich.setting', 'manual')
        if not config or config != 'manual':
            self.show_enrich_button = False
            return
        for lead in self:
            if not lead.active or not lead.email_from or lead.iap_enrich_done or lead.reveal_id or lead.probability == 100:
                lead.show_enrich_button = False
            else:
                lead.show_enrich_button = True

    @api.model
    def _iap_enrich_leads_cron(self):
        timeDelta = fields.datetime.now() - datetime.timedelta(hours=1)
        # Get all leads not lost nor won (lost: active = False)
        leads = self.search([
            ('iap_enrich_done', '=', False),
            ('reveal_id', '=', False),
            ('probability', '<', 100),
            ('create_date', '>', timeDelta)
        ])
        leads.iap_enrich(from_cron=True)

    def iap_enrich(self, from_cron=False):
        lead_emails = {}
        for lead in self:
            # If lead is lost, active == False, but is anyway removed from the search in the cron.
            if lead.probability == 100 or lead.iap_enrich_done:
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
                iap_response = self.env['iap.services']._iap_request_enrich(lead_emails)
            except iap_tools.InsufficientCreditError:
                _logger.info('Sent batch %s enrich requests: failed because of credit', len(lead_emails))
                if not from_cron:
                    data = {
                        'url': self.env['iap.services'].iap_get_service_credits_url('reveal'),
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
            lead_fields = ['partner_name', 'reveal_id', 'street', 'city', 'zip']
            iap_fields = ['name', 'clearbit_id', 'location', 'city', 'postal_code']
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

            template_values = iap_data
            template_values['flavor_text'] = _("Lead enriched based on email address")
            lead.message_post_with_view(
                'iap_mail.enrich_company',
                values=template_values,
                subtype_id=self.env.ref('mail.mt_note').id
            )
