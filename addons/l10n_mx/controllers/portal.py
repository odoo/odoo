from odoo.addons.portal.controllers import portal
from odoo.http import request

class CustomerPortal(portal.CustomerPortal):

    def _get_mandatory_fields(self):
        # EXTENDS 'portal'
        try:
            country_id = int(request.env.context.get('portal_form_country_id', ''))
        except ValueError:
            country_id = None

        mandatory_fields = super()._get_mandatory_fields()
        if country_id and request.env['res.country'].sudo().browse(country_id).code == 'MX':
            mandatory_fields += ['zipcode', 'vat']
        return mandatory_fields

    def _get_optional_fields(self):
        # EXTENDS 'portal'
        try:
            country_id = int(request.env.context.get('portal_form_country_id', ''))
        except ValueError:
            country_id = None

        optional_fields = super()._get_optional_fields()
        if country_id and request.env['res.country'].sudo().browse(country_id).code == 'MX':
            optional_fields = [field for field in optional_fields if field not in ['zipcode', 'vat']]
        return optional_fields
