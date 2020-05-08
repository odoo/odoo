# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import json
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    partner_gid = fields.Integer('Company database ID')
    additional_info = fields.Char('Additional info')

    @api.model
    def _replace_location_code_by_id(self, record):
        record['country_id'], record['state_id'] = self._find_country_data(
            state_code=record.pop('state_code', False),
            state_name=record.pop('state_name', False),
            country_code=record.pop('country_code', False),
            country_name=record.pop('country_name', False)
        )
        return record

    @api.model
    def _format_data_company(self, company):
        self._replace_location_code_by_id(company)

        if company.get('child_ids'):
            child_ids = []
            for child in company.get('child_ids'):
                child_ids.append(self._replace_location_code_by_id(child))
            company['child_ids'] = child_ids

        if company.get('additional_info'):
            company['additional_info'] = json.dumps(company['additional_info'])

        return company

    @api.model
    def _find_country_data(self, state_code, state_name, country_code, country_name):
        country = self.env['res.country'].search([['code', '=ilike', country_code]])
        if not country:
            country = self.env['res.country'].search([['name', '=ilike', country_name]])

        state_id = False
        country_id = False
        if country:
            country_id = {
                'id': country.id,
                'display_name': country.display_name
            }
            if state_name or state_code:
                state = self.env['res.country.state'].search([
                    ('country_id', '=', country_id.get('id')),
                    '|',
                    ('name', '=ilike', state_name),
                    ('code', '=ilike', state_code)
                ], limit=1)

                if state:
                    state_id = {
                        'id': state.id,
                        'display_name': state.display_name
                    }
        else:
            _logger.info('Country code not found: %s', country_code)

        return country_id, state_id

    @api.model
    def autocomplete(self, query):
        suggestions, error = self.env['iap.services']._iap_partner_autocomplete('partner_autocomplete_search', query=query)
        if suggestions:
            results = []
            for suggestion in suggestions:
                results.append(self._format_data_company(suggestion))
            return results
        else:
            return []

    @api.model
    def enrich_company(self, company_domain, partner_gid, vat):
        response, error = self.env['iap.services']._iap_partner_autocomplete(
            'partner_autocomplete_search_enrich', domain=company_domain,
            partner_gid=partner_gid, vat=vat)
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
    def read_by_vat(self, vat):
        vies_vat_data, error = self.env['iap.services']._iap_partner_autocomplete('partner_autocomplete_search_enrich', vat=vat)
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
        partner_country_code = self.country_id and self.country_id.code
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
