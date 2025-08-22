# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging

from psycopg2 import OperationalError

from odoo import _, api, fields, models, modules, tools
from odoo.addons.iap.tools import iap_tools

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    iap_enrich_done = fields.Boolean(string='Enrichment done', help='Whether IAP service for lead enrichment based on email has been performed on this lead.')
    show_enrich_button = fields.Boolean(string='Allow manual enrich', compute="_compute_show_enrich_button")

    @api.depends('email_from', 'probability', 'iap_enrich_done', 'reveal_id')
    def _compute_show_enrich_button(self):
        for lead in self:
            if not lead.active or not lead.email_from or lead.email_state == 'incorrect' or lead.iap_enrich_done or lead.reveal_id or lead.probability == 100:
                lead.show_enrich_button = False
            else:
                lead.show_enrich_button = True

    @api.model
    def _iap_enrich_leads_cron(self, enrich_hours_delay=24, leads_batch_size=1000):
        timeDelta = self.env.cr.now() - datetime.timedelta(hours=enrich_hours_delay)
        # Get all leads not lost nor won (lost: active = False)
        leads = self.search([
            ('iap_enrich_done', '=', False),
            ('reveal_id', '=', False),
            '|', ('probability', '<', 100), ('probability', '=', False),
            ('create_date', '>', timeDelta)
        ], limit=leads_batch_size)
        leads.iap_enrich(from_cron=True)

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        enrich_mode = self.env['ir.config_parameter'].sudo().get_param('crm.iap.lead.enrich.setting', 'auto')
        if enrich_mode == 'auto':
            cron = self.env.ref('crm_iap_enrich.ir_cron_lead_enrichment', raise_if_not_found=False)
            if cron:
                cron._trigger()
        return leads

    def iap_enrich(self, from_cron=False):
        # Split self in a list of sub-recordsets or 50 records to prevent timeouts
        batches = [self[index:index + 50] for index in range(0, len(self), 50)]
        for leads in batches:
            lead_emails = {}
            with self._cr.savepoint():
                try:
                    self._cr.execute(
                        "SELECT 1 FROM {} WHERE id in %(lead_ids)s FOR UPDATE NOWAIT".format(self._table),
                        {'lead_ids': tuple(leads.ids)}, log_exceptions=False)
                    for lead in leads:
                        # If lead is lost, active == False, but is anyway removed from the search in the cron.
                        if lead.probability == 100 or lead.iap_enrich_done:
                            continue
                        # Skip if no email (different from wrong email leading to no email_normalized)
                        if not lead.email_from:
                            continue

                        normalized_email = tools.email_normalize(lead.email_from)
                        if not normalized_email:
                            lead.write({'iap_enrich_done': True})
                            lead.message_post_with_source(
                                'crm_iap_enrich.mail_message_lead_enrich_no_email',
                                subtype_xmlid='mail.mt_note',
                            )
                            continue

                        email_domain = normalized_email.split('@')[1]
                        # Discard domains of generic email providers as it won't return relevant information
                        if email_domain in iap_tools._MAIL_PROVIDERS:
                            lead.write({'iap_enrich_done': True})
                            lead.message_post_with_source(
                                'crm_iap_enrich.mail_message_lead_enrich_notfound',
                                subtype_xmlid='mail.mt_note',
                            )
                        else:
                            lead_emails[lead.id] = email_domain

                    if lead_emails:
                        try:
                            iap_response = self.env['iap.enrich.api']._request_enrich(lead_emails)
                        except iap_tools.InsufficientCreditError:
                            _logger.info('Lead enrichment failed because of insufficient credit')
                            if not from_cron:
                                self.env['iap.account']._send_no_credit_notification(
                                    service_name='reveal',
                                    title=_("Not enough credits for Lead Enrichment"))
                            # Since there are no credits left, there is no point to process the other batches
                            break
                        except Exception as e:
                            if not from_cron:
                                self.env['iap.account']._send_error_notification(
                                    message=_('An error occurred during lead enrichment'))
                            _logger.info('An error occurred during lead enrichment: %s', e)
                        else:
                            if not from_cron:
                                self.env['iap.account']._send_success_notification(
                                    message=_("The leads/opportunities have successfully been enriched"))
                            _logger.info('Batch of %s leads successfully enriched', len(lead_emails))
                            self._iap_enrich_from_response(iap_response)
                except OperationalError:
                    _logger.error('A batch of leads could not be enriched :%s', repr(leads))
                    continue
            # Commit processed batch to avoid complete rollbacks and therefore losing credits.
            if not modules.module.current_test:
                self.env.cr.commit()

    @api.model
    def _iap_enrich_from_response(self, iap_response):
        """ Handle from the service and enrich the lead accordingly

        :param iap_response: dict{lead_id: company data or False}
        """
        for lead in self.search([('id', 'in', list(iap_response.keys()))]):  # handle unlinked data by performing a search
            iap_data = iap_response.get(str(lead.id))
            if not iap_data:
                lead.write({'iap_enrich_done': True})
                lead.message_post_with_source(
                    'crm_iap_enrich.mail_message_lead_enrich_notfound',
                    subtype_xmlid='mail.mt_note',
                )
                continue

            values = {'iap_enrich_done': True}
            lead_fields = ['partner_name', 'reveal_id', 'street', 'city', 'zip']
            iap_fields = ['name', 'clearbit_id', 'location', 'city', 'postal_code']
            for lead_field, iap_field in zip(lead_fields, iap_fields):
                if not lead[lead_field] and iap_data.get(iap_field):
                    values[lead_field] = iap_data[iap_field]

            if not lead.phone and iap_data.get('phone_numbers'):
                values['phone'] = iap_data['phone_numbers'][0]
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
            lead.message_post_with_source(
                'iap_mail.enrich_company',
                render_values=template_values,
                subtype_xmlid='mail.mt_note',
            )

    def _merge_get_fields_specific(self):
        return {
            ** super()._merge_get_fields_specific(),
            'iap_enrich_done': lambda fname, leads: any(lead.iap_enrich_done for lead in leads),
        }
