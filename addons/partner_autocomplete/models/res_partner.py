# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import logging
import requests
from psycopg2 import OperationalError

from odoo import api, fields, models, tools, _
from odoo.addons.iap.tools import iap_tools

_logger = logging.getLogger(__name__)

PARTNER_AC_TIMEOUT = 5


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    iap_enrich_done = fields.Boolean(string='Enrichment done',
        help='Whether IAP service for company enrichment based on vat / name / domain has been performed on this company.')
    partner_gid = fields.Integer('Company database ID')
    additional_info = fields.Char('Additional info')

    @api.model
    def _iap_replace_location_codes(self, iap_data):
        country_code, country_name = iap_data.pop('country_code', False), iap_data.pop('country_name', False)
        state_code, state_name = iap_data.pop('state_code', False), iap_data.pop('state_name', False)

        country, state = None, None
        if country_code:
            country = self.env['res.country'].search([['code', '=ilike', country_code]])
        if not country and country_name:
            country = self.env['res.country'].search([['name', '=ilike', country_name]])

        if country:
            if state_code:
                state = self.env['res.country.state'].search([
                    ('country_id', '=', country.id), ('code', '=ilike', state_code)
                ], limit=1)
            if not state and state_name:
                state = self.env['res.country.state'].search([
                    ('country_id', '=', country.id), ('name', '=ilike', state_name)
                ], limit=1)
        else:
            _logger.info('Country code not found: %s', country_code)

        if country:
            iap_data['country_id'] = {'id': country.id, 'display_name': country.display_name}
        if state:
            iap_data['state_id'] = {'id': state.id, 'display_name': state.display_name}

        return iap_data

    @api.model
    def _iap_replace_logo(self, iap_data):
        if iap_data.get('logo'):
            try:
                iap_data['image_1920'] = base64.b64encode(
                    requests.get(iap_data['logo'], timeout=PARTNER_AC_TIMEOUT).content
                )
            except Exception:
                iap_data['image_1920'] = False
            finally:
                iap_data.pop('logo')
            # avoid keeping falsy images (may happen that a blank page is returned that leads to an incorrect image)
            if iap_data['image_1920']:
                try:
                    tools.base64_to_image(iap_data['image_1920'])
                except Exception:
                    iap_data.pop('image_1920')
        return iap_data

    @api.model
    def _format_data_company(self, iap_data):
        self._iap_replace_location_codes(iap_data)

        if iap_data.get('child_ids'):
            child_ids = []
            for child in iap_data.get('child_ids'):
                child_ids.append(self._iap_replace_location_codes(child))
            iap_data['child_ids'] = child_ids

        if iap_data.get('additional_info'):
            iap_data['additional_info'] = json.dumps(iap_data['additional_info'])

        return iap_data

    @api.model
    def autocomplete(self, query, timeout=15):
        suggestions, _ = self.env['iap.autocomplete.api']._request_partner_autocomplete('search', {
            'query': query,
        }, timeout=timeout)
        if suggestions:
            results = []
            for suggestion in suggestions:
                results.append(self._format_data_company(suggestion))
            return results
        else:
            return []

    @api.model
    def enrich_company(self, company_domain, partner_gid, vat, timeout=15):
        response, error = self.env['iap.autocomplete.api']._request_partner_autocomplete('enrich', {
            'domain': company_domain,
            'partner_gid': partner_gid,
            'vat': vat,
        }, timeout=timeout)
        if response and response.get('company_data'):
            result = self._format_data_company(response.get('company_data'))
        else:
            result = {}

        if response and response.get('credit_error'):
            result.update({
                'error': True,
                'error_message': 'Insufficient Credit'
            })
        elif error:
            result.update({
                'error': True,
                'error_message': error
            })

        return result

    @api.model
    def read_by_vat(self, vat, timeout=15):
        vies_vat_data, _ = self.env['iap.autocomplete.api']._request_partner_autocomplete('search_vat', {
            'vat': vat,
        }, timeout=timeout)
        if vies_vat_data:
            return [self._format_data_company(vies_vat_data)]
        else:
            return []

    @api.model
    def _is_company_in_europe(self, country_code):
        country = self.env['res.country'].search([('code', '=ilike', country_code)])
        if country:
            country_id = country.id
            europe = self.env.ref('base.europe')
            if not europe:
                europe = self.env["res.country.group"].search([('name', '=', 'Europe')], limit=1)
            if not europe or country_id not in europe.country_ids.ids:
                return False
        return True

    def _is_vat_syncable(self, vat):
        vat_country_code = vat[:2]
        partner_country_code = self.country_id.code if self.country_id else ''
        return self._is_company_in_europe(vat_country_code) and (partner_country_code == vat_country_code or not partner_country_code)

    def _is_synchable(self):
        already_synched = self.env['res.partner.autocomplete.sync'].search([('partner_id', '=', self.id), ('synched', '=', True)])
        return self.is_company and self.partner_gid and not already_synched

    def _update_autocomplete_data(self, vat):
        self.ensure_one()
        if vat and self._is_synchable() and self._is_vat_syncable(vat):
            self.env['res.partner.autocomplete.sync'].sudo().add_to_queue(self.id)

    @api.model_create_multi
    def create(self, vals_list):
        partners = super(ResPartner, self).create(vals_list)
        if len(vals_list) == 1:
            partners._update_autocomplete_data(vals_list[0].get('vat', False))
            if partners.additional_info:
                template_values = json.loads(partners.additional_info)
                template_values['flavor_text'] = _("Partner created by Odoo Partner Autocomplete Service")
                partners.message_post_with_view(
                    'iap_mail.enrich_company',
                    values=template_values,
                    subtype_id=self.env.ref('mail.mt_note').id,
                )
                partners.write({'additional_info': False})

        return partners

    def write(self, values):
        res = super(ResPartner, self).write(values)
        if len(self) == 1:
            self._update_autocomplete_data(values.get('vat', False))

        return res

    def _autocomplete_on_demand(self):
        ''' This method perform on demand enrichment on the existing partners, which are not
        already enriched and are of type company.
        '''
        # Filter out company records for which enrichment is yet to be done
        company_partners = self.filtered(lambda p: p.is_company and not p.iap_enrich_done)
        # Split self in a list of sub-recordset or 50 records to prevent timeouts
        batches = [company_partners[index:index + 50] for index in range(0, len(company_partners), 50)]
        partners_with_error = self.env['res.partner']
        Company = self.env['res.company']
        for partners in batches:
            # Flag to prevent enrichment on further batches if any current batch is interrupted due to no token / not enough credits
            no_credit_or_token = False
            with self.env.cr.savepoint():
                try:
                    self.env.cr.execute(
                        "SELECT 1 FROM {} WHERE id in %(partner_ids)s FOR UPDATE NOWAIT".format(self._table),
                        {'partner_ids': tuple(partners.ids)}, log_exceptions=False)
                    for partner in partners:
                        enrich_params = {'website': False, 'partner_gid': False, 'vat': False}

                        # First attempt to get basic details needed for enrichment, with help of VAT
                        if partner.vat:
                            vies_vat_data, error = self.env['iap.autocomplete.api']._request_partner_autocomplete('search_vat', {
                                'vat': partner.vat,
                            })
                            if error:
                                if error in ['Insufficient Credit', 'No account token']:
                                    # Since there are no credits left / no token, there is no point to process the other batches
                                    _logger.info('Batch containing partner ids %s cold not be enriched and failed with exception %s, further batches will not be processed', ', '.join(str(pid) for pid in partners.ids), error)
                                    no_credit_or_token = True
                                    break
                                else:
                                    partners_with_error |= partner
                                    continue
                            if vies_vat_data:
                                enrich_params.update({
                                    'website': vies_vat_data.get('website'),
                                    'partner_gid': vies_vat_data.get('partner_gid'),
                                    'vat': vies_vat_data.get('vat'),
                                })

                        # Second attempt to get basic details needed for enrichment, with help of partner name if vat not available or details not found by vat
                        if not enrich_params.get('vat') and partner.name:
                            suggestions, error = self.env['iap.autocomplete.api']._request_partner_autocomplete('search', {
                                'query': partner.name,
                            })
                            if error:
                                if error in ['Insufficient Credit', 'No account token']:
                                    # Since there are no credits left / no token, there is no point to process the other batches
                                    _logger.info('Batch containing partner ids %s cold not be enriched and failed with exception %s, further batches will not be processed', ', '.join(str(pid) for pid in partners.ids), error)
                                    no_credit_or_token = True
                                    break
                                else:
                                    partners_with_error |= partner
                                    continue
                            if suggestions and len(suggestions):
                                enrich_params.update({
                                    'website': suggestions[0].get('website'),
                                    'partner_gid': suggestions[0].get('partner_gid'),
                                    'vat': suggestions[0].get('vat'),
                                })

                        # If details like vat and website are still not found in both the attempts,
                        # try to get the company domain from partner's website or email
                        if not enrich_params.get('vat') and not enrich_params.get('website'):
                            company_domain = partner.website and tools.url_domain_extract(partner.website) or tools.email_domain_extract(partner.email)
                            if company_domain and company_domain not in iap_tools._MAIL_DOMAIN_BLACKLIST:
                                enrich_params['website'] = company_domain

                        # Finally, perform enrichment if details are enough
                        if enrich_params.get('website') or enrich_params.get('partner_gid') or enrich_params.get('vat'):
                            company_data = self.enrich_company(enrich_params['website'], enrich_params['partner_gid'], enrich_params['vat'])
                            if company_data.get('error'):
                                if company_data['error_message'] in ['Insufficient Credit', 'No account token']:
                                    # Since there are no credits left / no token, there is no point to process the other batches
                                    _logger.info('Batch containing partner ids %s cold not be enriched and failed with exception %s, further batches will not be processed', ', '.join(str(pid) for pid in partners.ids), error)
                                    no_credit_or_token = True
                                    break
                                else:
                                    partners_with_error |= partner
                                    continue
                            else:
                                additional_data = company_data.pop('additional_info', False)
                                # Keep only truthy values that are not already set on the partner
                                if not partner.image_1920:
                                    self._iap_replace_logo(company_data)

                                company_data = {field: value for field, value in company_data.items()
                                                if field in partner._fields and value and not partner[field]}

                                # for company and childs: from state_id / country_id name_get like to IDs
                                company_data.update(Company._enrich_extract_m2o_id(company_data, ['state_id', 'country_id']))
                                if company_data.get('child_ids'):
                                    company_data['child_ids'] = [
                                        dict(child_data, **Company._enrich_extract_m2o_id(child_data, ['state_id', 'country_id']))
                                        for child_data in company_data['child_ids']
                                    ]

                                # handle o2m values, e.g. {'bank_ids': ['acc_number': 'BE012012012', 'acc_holder_name': 'MyWebsite']}
                                Company._enrich_replace_o2m_creation(company_data)

                                # update the partner details, and log the note
                                partner.write(company_data)

                                if additional_data:
                                    template_values = json.loads(additional_data)
                                    template_values['flavor_text'] = _("Partner enriched by Odoo Partner Autocomplete Service")
                                    partner.message_post_with_view(
                                        'iap_mail.enrich_company',
                                        values=template_values,
                                        subtype_id=self.env.ref('mail.mt_note').id,
                                    )
                        else:
                            # simply log a note if could not enrich the partner from available details
                            partner.message_post_with_view(
                                'partner_autocomplete.mail_message_partner_enrich_notfound',
                                subtype_id=self.env.ref('mail.mt_note').id
                            )
                        # Mark the record as enriched
                        partner.iap_enrich_done = True

                    # No need to process further batches if there's no enough credit / no token available
                    if no_credit_or_token:
                        self.env['bus.bus'].sendone(
                            (self.env.cr.dbname, 'res.partner', self.env.user.partner_id.id),
                            {'type': 'simple_notification', 'title': _("Warning"),
                             'message': _("Enrichment interrupted due to invalid Token / Insufficient Credits. Kindly contact the Administrator.")}
                        )
                        break
                except OperationalError:
                    _logger.error('A batch of companies could not be enriched :%s', repr(partners))
                    continue
            # Commit processed batch to avoid complete rollbacks and therefore losing credits.
            if not self.env.registry.in_test_mode():
                self.env.cr.commit()

        if partners_with_error:
            parner_names = '\n'.join(['%s (ID - %s)' % (p.name, p.id) for p in partners_with_error])
            notif_message = _('Error occurred during enrichment process for these partners:\n\n%s', parner_names)
            _logger.info(notif_message)

            self.env['bus.bus'].sendone(
                (self.env.cr.dbname, 'res.partner', self.env.user.partner_id.id),
                {'type': 'simple_notification', 'title': _("Warning"),
                 'message': notif_message}
            )
