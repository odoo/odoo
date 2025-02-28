# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.controllers.portal import CustomerPortal
from odoo.http import request

class CustomerPortalBr(CustomerPortal):

    def _get_mandatory_fields(self):
        """Extend mandatory fields to add the vat in case the website and the customer are from brazil"""
        mandatory_fields = super()._get_mandatory_fields()

        if request.params.get('country_id'):
            country = request.env['res.country'].browse(int(request.params['country_id']))
            if request.website.sudo().company_id.country_id.code == "BR" and country.code == "BR" and "vat" not in mandatory_fields:
                mandatory_fields += ['vat']

        return mandatory_fields

    def _get_optional_fields(self):
        """Extend optional fields to add the identification type to avoid having the unknown field error"""
        optional_fields = super()._get_optional_fields()
        if request.website.sudo().company_id.country_id.code == "BR" and 'l10n_latam_identification_type_id' not in optional_fields:
            optional_fields += ['l10n_latam_identification_type_id']
        return optional_fields

    def details_form_validate(self, data, partner_creation=False):
        error, error_message = super().details_form_validate(data, partner_creation)

        website = request.env['website'].get_current_website()
        # This is needed so that the field is correctly write on the partner
        if data.get('l10n_latam_identification_type_id') and website.company_id.country_code == 'BR':
            data['l10n_latam_identification_type_id'] = int(data['l10n_latam_identification_type_id'])
        return error, error_message

    def _prepare_portal_layout_values(self):
        portal_layout_values = super()._prepare_portal_layout_values()
        website = request.env['website'].get_current_website()
        if website.company_id.country_code == 'BR':
            portal_layout_values['identification_types'] = request.env['l10n_latam.identification.type'].search(['|', ('country_id', '=', False), ('country_id.code', '=', 'BR')])
        return portal_layout_values
