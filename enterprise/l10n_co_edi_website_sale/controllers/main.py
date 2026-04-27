from odoo import http
from odoo.http import request
from odoo.tools import _

from odoo.addons.website_sale.controllers.main import WebsiteSale


class L10nCOWebsiteSale(WebsiteSale):

    def _get_mandatory_billing_address_fields(self, country_sudo):
        mandatory_fields = super()._get_mandatory_billing_address_fields(country_sudo)
        company_country = request.website.sudo().company_id.account_fiscal_country_id
        if country_sudo.code == 'CO' and country_sudo.id == company_country.id:
            mandatory_fields |= {
                "vat",
                "city_id",
                "state_id",
                "l10n_latam_identification_type_id",
            }
            mandatory_fields.remove("city")
        return mandatory_fields

    def _get_mandatory_delivery_address_fields(self, country_sudo):
        mandatory_fields = super()._get_mandatory_delivery_address_fields(country_sudo)
        company_country = request.website.sudo().company_id.account_fiscal_country_id
        if country_sudo.code == 'CO' and country_sudo.id == company_country.id:
            mandatory_fields |= {
                "city_id",
                "state_id",
            }
            mandatory_fields.remove("city")
        return mandatory_fields

    def _parse_form_data(self, form_data):
        # This is needed so that the field is correctly read as list from the request
        if form_data.get('l10n_co_edi_obligation_type_ids'):
            form_data['l10n_co_edi_obligation_type_ids'] = request.httprequest.form.getlist('l10n_co_edi_obligation_type_ids', int)
        # Set default values for fiscal regimen and obligation types when identification type is not NIT
        nit_id_type = request.env['l10n_latam.identification.type'].sudo().search([('name', '=', 'NIT'), ('country_id.code', '=', 'CO')], limit=1)
        id_type_id = form_data.get('l10n_latam_identification_type_id')
        if id_type_id and nit_id_type and int(id_type_id) != nit_id_type.id:
            default_obligations = ['R-99-PN']
            default_obligations_ids = request.env['l10n_co_edi.type_code'].sudo().search([('name', 'in', default_obligations)])
            form_data.update({
                'l10n_co_edi_fiscal_regimen': '49',  # No Aplica
                'l10n_co_edi_obligation_type_ids': default_obligations_ids,
            })
        return super()._parse_form_data(form_data)

    def _prepare_address_form_values(self, order_sudo, partner_sudo, address_type, **kwargs):
        rendering_values = super()._prepare_address_form_values(
            order_sudo, partner_sudo, address_type=address_type, **kwargs
        )

        if request.website.sudo().company_id.account_fiscal_country_id.code == "CO":
            LatamIdentificationType = request.env['l10n_latam.identification.type'].sudo()
            can_edit_vat = rendering_values['can_edit_vat']
            state = request.env['res.country.state'].browse(rendering_values['state_id'])
            city = partner_sudo.city_id
            ResCity = request.env['res.city'].sudo()

            rendering_values.update({
                'identification_types': LatamIdentificationType.search([
                    '|', ('country_id', '=', False), ('country_id.code', '=', 'CO')
                ]) if can_edit_vat else LatamIdentificationType,
                'vat_label': request.env._('Identification Number'),
                'obligation_types': request.env['l10n_co_edi.type_code'].sudo().search([]),
                'selected_obligation_types_ids': request.httprequest.form.getlist('l10n_co_edi_obligation_type_ids', int) or [],
                'fiscal_regimen_selection': request.env["res.partner"]._fields["l10n_co_edi_fiscal_regimen"].selection,
                'state': state,
                'state_cities': ResCity.search([('state_id', '=', state.id)]) if state else ResCity,
                'city': city,
            })
        return rendering_values

    def _get_vat_validation_fields(self):
        fnames = super()._get_vat_validation_fields()
        if request.website.sudo().company_id.account_fiscal_country_id.code == "CO":
            fnames.add('l10n_latam_identification_type_id')
            fnames.add('name')
        return fnames

    def _validate_address_values(self, address_values, partner_sudo, address_type, *args, **kwargs):
        invalid_fields, missing_fields, error_messages = super()._validate_address_values(
            address_values, partner_sudo, address_type, *args, **kwargs
        )

        if request.website.sudo().company_id.account_fiscal_country_id.code == "CO" and address_type == 'billing':
            if missing_fields and any(
                fname in missing_fields
                for fname in [
                    'l10n_latam_identification_type_id', 'l10n_co_edi_obligation_type_ids', 'l10n_co_edi_fiscal_regimen'
                ]
            ):
                return invalid_fields, missing_fields, error_messages
            id_type = request.env['l10n_latam.identification.type'].browse(
                address_values.get("l10n_latam_identification_type_id")
            )
            if id_type and id_type.name == 'NIT':
                if not address_values.get('l10n_co_edi_obligation_type_ids'):
                    missing_fields.add('l10n_co_edi_obligation_type_ids')
                if not address_values.get('l10n_co_edi_fiscal_regimen'):
                    missing_fields.add('l10n_co_edi_fiscal_regimen')
                if not address_values.get('company_name'):
                    missing_fields.add('company_name')
                if len(missing_fields):
                    error_messages.append(_("Indicated Fields are missing."))

        return invalid_fields, missing_fields, error_messages

    @http.route(
        ['/shop/l10n_co_state_infos/<model("res.country.state"):state>'],
        type="json",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def l10n_co_state_infos(self, state, **kw):
        cities = request.env["res.city"].sudo().search([("state_id", "=", state.id)])
        return {'cities': [(c.id, c.name, c.l10n_co_edi_code) for c in cities]}
