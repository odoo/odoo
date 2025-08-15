import logging
import re

from stdnum.eu.vat import check_vies

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

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

        if country:
            iap_data['country_id'] = {'id': country.id, 'display_name': country.display_name}
        if state:
            iap_data['state_id'] = {'id': state.id, 'display_name': state.display_name}

        return iap_data

    @api.model
    def _iap_replace_industry_code(self, iap_data):
        if industry_code := iap_data.pop('industry_code', False):
            if industry := self.env.ref(f'base.res_partner_industry_{industry_code}', raise_if_not_found=False):
                iap_data['industry_id'] = {'id': industry.id, 'display_name': industry.display_name}
        return iap_data

    @api.model
    def _iap_replace_language_codes(self, iap_data):
        if lang := iap_data.pop('preferred_language', False):
            if installed_lang := (
                self.env['res.lang'].search([('code', '=', lang), ('iso_code', '=', lang)])  # specific lang (e.g.: fr_BE)
                or
                self.env['res.lang'].search([('code', 'ilike', lang[:2]), ('iso_code', 'ilike', lang[:2])], limit=1)  # fallback to generic lang (e.g. fr)
            ):
                iap_data['lang'] = installed_lang.code
        return iap_data

    @api.model
    def _format_data_company(self, iap_data):
        self._iap_replace_location_codes(iap_data)
        self._iap_replace_industry_code(iap_data)
        self._iap_replace_language_codes(iap_data)
        return iap_data

    # Deprecated since DnB
    @api.model
    def autocomplete(self, query, timeout=15):
        return []

    # Deprecated since DnB
    @api.model
    def enrich_company(self, company_domain, partner_gid, vat, timeout=15):
        return {}

    # Deprecated since DnB
    @api.model
    def read_by_vat(self, vat, timeout=15):
        return []

    # Deprecated since DnB
    def check_gst_in(self, vat):
        return False

    @api.model
    def autocomplete_by_name(self, query, query_country_id, timeout=15):
        if query_country_id is False:  # If it's 0, we purposely do not want to filter on the country
            query_country_id = self.env.company.country_id.id
        query_country_code = self.env['res.country'].browse(query_country_id).code
        response, _ = self.env['iap.autocomplete.api']._request_partner_autocomplete('search_by_name', {
            'query': query,
            'query_country_code': query_country_code,
        }, timeout=timeout)
        if response and not response.get("error"):
            results = []
            for suggestion in response.get("data"):
                results.append(self._format_data_company(suggestion))
            return results
        else:
            return []

    @api.model
    def autocomplete_by_vat(self, vat, query_country_id, timeout=15):
        query_country_id = query_country_id or self.env.company.country_id.id
        query_country_code = self.env['res.country'].browse(query_country_id).code
        response, _ = self.env['iap.autocomplete.api']._request_partner_autocomplete('search_by_vat', {
            'query': vat,
            'query_country_code': query_country_code,
        }, timeout=timeout)
        if response and not response.get("error"):
            results = []
            for suggestion in response.get("data"):
                results.append(self._format_data_company(suggestion))
            return results
        else:
            vies_result = None
            try:
                _logger.info('Calling VIES service to check VAT for autocomplete: %s', vat)
                vies_result = check_vies(vat, timeout=timeout)
            except Exception:
                _logger.exception("Failed VIES VAT check.")
            if vies_result:
                name = vies_result['name']
                if vies_result['valid'] and name != '---':
                    address = list(filter(bool, vies_result['address'].split('\n')))
                    street = address[0]
                    zip_city_record = next(filter(lambda addr: re.match(r'^\d.*', addr), address[1:]), None)
                    zip_city = zip_city_record.split(' ', 1) if zip_city_record else [None, None]
                    street2 = next((addr for addr in filter(lambda addr: addr != zip_city_record, address[1:])), None)
                    return [self._iap_replace_location_codes({
                        'name': name,
                        'vat': vat,
                        'street': street,
                        'street2': street2,
                        'city': zip_city[1],
                        'zip': zip_city[0],
                        'country_code': vies_result['countryCode'],
                    })]
            return []

    @api.model
    def _process_enriched_response(self, response, error):
        if response and response.get('data'):
            result = self._format_data_company(response.get('data'))
        else:
            result = {}

        if response and response.get('credit_error'):
            result.update({
                'error': True,
                'error_message': 'Insufficient Credit'
            })
        elif response and response.get('error'):
            result.update({
                'error': True,
                'error_message': _('Unable to enrich company (no credit was consumed).'),
            })
        elif error:
            result.update({
                'error': True,
                'error_message': error
            })
        return result

    @api.model
    def enrich_by_duns(self, duns, timeout=15):
        response, error = self.env['iap.autocomplete.api']._request_partner_autocomplete('enrich_by_duns', {
            'duns': duns,
        }, timeout=timeout)
        return self._process_enriched_response(response, error)

    @api.model
    def enrich_by_gst(self, gst, timeout=15):
        response, error = self.env['iap.autocomplete.api']._request_partner_autocomplete('enrich_by_gst', {
            'gst': gst,
        }, timeout=timeout)
        return self._process_enriched_response(response, error)

    @api.model
    def enrich_by_domain(self, domain, timeout=15):
        response, error = self.env['iap.autocomplete.api']._request_partner_autocomplete('enrich_by_domain', {
            'domain': domain,
        }, timeout=timeout)
        return self._process_enriched_response(response, error)

    def iap_partner_autocomplete_add_tags(self, unspsc_codes):
        """Called by JS to create the activity tags from the UNSPSC codes"""
        self.ensure_one()

        # If the UNSPSC module is installed, we might have a translation, so let's use it
        if self.env['ir.module.module']._get('product_unspsc').state == 'installed':
            tag_names = self.env['product.unspsc.code']\
                            .with_context(active_test=False)\
                            .search([('code', 'in', [unspsc_code for unspsc_code, __ in unspsc_codes])])\
                            .mapped('name')
        # If it's not, then we use the default English name provided by DnB
        else:
            tag_names = [unspsc_name for __, unspsc_name in unspsc_codes]

        tag_ids = self.env['res.partner.category']
        for tag_name in tag_names:
            if existing_tag := self.env['res.partner.category'].search([('name', '=', tag_name)]):
                tag_ids |= existing_tag
            else:
                tag_ids |= self.env['res.partner.category'].create({'name': tag_name})
        self.category_id = tag_ids

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)

        if view_type == 'form':
            for node in arch.xpath(
                "//field[@name='name']"
                "|//field[@name='vat']"
            ):
                node.attrib['widget'] = 'field_partner_autocomplete'

        return arch, view
