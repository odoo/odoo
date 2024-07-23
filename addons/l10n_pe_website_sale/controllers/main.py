# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request, route


class L10nPEWebsiteSale(WebsiteSale):

    def _get_mandatory_billing_address_fields(self, country_sudo):
        mandatory_fields = super()._get_mandatory_billing_address_fields(country_sudo)
        if request.website.sudo().company_id.country_id.code != 'PE':
            return mandatory_fields

        # For Peruvian company, the VAT is required for all the partners
        mandatory_fields.add('vat')
        if country_sudo.code == 'PE':
            mandatory_fields |= {
                'state_id', 'city_id', 'l10n_pe_district', 'l10n_latam_identification_type_id',
            }
            mandatory_fields.remove('city')
        return mandatory_fields

    def _get_mandatory_delivery_address_fields(self, country_sudo):
        mandatory_fields = super()._get_mandatory_delivery_address_fields(country_sudo)
        if request.website.sudo().company_id.country_id.code != 'PE':
            return mandatory_fields

        if country_sudo.code == 'PE':
            mandatory_fields |= {'state_id', 'city_id', 'l10n_pe_district'}
            mandatory_fields.remove('city')
        return mandatory_fields

    def _prepare_address_form_values(self, order_sudo, partner_sudo, address_type, **kwargs):
        rendering_values = super()._prepare_address_form_values(
            order_sudo, partner_sudo, address_type=address_type, **kwargs
        )
        if request.website.sudo().company_id.country_id.code != 'PE':
            return rendering_values

        if address_type == 'billing':
            can_edit_vat = rendering_values['can_edit_vat']
            LatamIdentificationType = request.env['l10n_latam.identification.type'].sudo()
            rendering_values.update({
                'identification_types': LatamIdentificationType.search([
                    '|', ('country_id', '=', False), ('country_id.code', '=', 'PE')
                ]) if can_edit_vat else LatamIdentificationType,
                'vat_label': request.env._("Identification Number"),
            })

        state = request.env['res.country.state'].browse(rendering_values['state_id'])
        city = partner_sudo.city_id
        ResCity = request.env['res.city'].sudo()
        District = request.env['l10n_pe.res.city.district'].sudo()
        rendering_values.update({
            'state': state,
            'state_cities': ResCity.search([('state_id', '=', state.id)]) if state else ResCity,
            'city': city,
            'city_districts': District.search([('city_id', '=', city.id)]) if city else District,
        })
        return rendering_values

    def _get_vat_validation_fields(self):
        fnames = super()._get_vat_validation_fields()
        if request.website.sudo().company_id.account_fiscal_country_id.code == 'PE':
            fnames.add('l10n_latam_identification_type_id')
            fnames.add('name')
        return fnames

    @route(
        '/shop/state_infos/<model("res.country.state"):state>',
        type='json',
        auth='public',
        methods=['POST'],
        website=True,
    )
    def state_infos(self, state, **kw):
        states = request.env['res.city'].sudo().search([('state_id', '=', state.id)])
        return {'cities': [(c.id, c.name, c.l10n_pe_code) for c in states]}

    @route(
        '/shop/city_infos/<model("res.city"):city>',
        type='json',
        auth='public',
        methods=['POST'],
        website=True,
    )
    def city_infos(self, city, **kw):
        districts = request.env['l10n_pe.res.city.district'].sudo().search([('city_id', '=', city.id)])
        return {'districts': [(d.id, d.name, d.code) for d in districts]}
