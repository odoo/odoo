from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class WebsiteSaleBr(WebsiteSale):

    def _get_mandatory_fields_billing(self, country_id=False):
        """Extend mandatory fields to add the vat in case the website and the customer are from brazil"""
        mandatory_fields = super()._get_mandatory_fields_billing(country_id)

        if request.params.get('country_id'):
            country = request.env['res.country'].browse(int(request.params['country_id']))
            if request.website.sudo().company_id.country_id.code == "BR" and country.code == "BR" and "vat" not in mandatory_fields:
                mandatory_fields += ['vat']
            # Needed because the user could put brazil and then change to another country, we don't want the field to stay mandatory
            elif 'vat' in mandatory_fields and country.code != 'BR':
                mandatory_fields.remove('vat')
        return mandatory_fields

    def values_postprocess(self, order, mode, values, errors, error_msg):
        post, errors, error_msg = super().values_postprocess(order, mode, values, errors, error_msg)
        website = request.env['website'].get_current_website()
        # This is needed so that the field is correctly write on the partner
        if values.get('l10n_latam_identification_type_id') and website.company_id.country_code == 'BR':
            post['l10n_latam_identification_type_id'] = values['l10n_latam_identification_type_id']

        return post, errors, error_msg

    def _get_country_related_render_values(self, kw, render_values):
        country_related_values = super()._get_country_related_render_values(kw, render_values)
        website = request.env['website'].get_current_website()
        if website.company_id.country_code == 'BR':
            country_related_values['identification_types'] = request.env['l10n_latam.identification.type'].search(['|', ('country_id', '=', False), ('country_id.code', '=', 'BR')])
        return country_related_values
