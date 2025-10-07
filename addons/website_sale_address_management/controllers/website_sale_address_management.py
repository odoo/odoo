# -- coding: utf-8 --
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2023-TODAY Cybrosys Technologies (<https://www.cybrosys.com>)
#    Author: Cybrosys (<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
################################################################################
from odoo import http, tools, _
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSale(http.Controller):
    """class used to monkey patch functions in class WebsiteSale"""

    def checkout_form_validate(self, mode, all_form_values, data):
        """function to monkey patch function checkout_form_validate and
        remove not required fields from list required_fields"""
        # mode: tuple ('new|edit', 'billing|shipping')
        # all_form_values: all values before preprocess
        # data: values after preprocess
        error = dict()
        error_message = []
        if not data.get('country_id'):
            default_country_id = request.env[
                'ir.config_parameter'].sudo().get_param('default_country_id')
            if default_country_id:
                data['country_id'] = int(default_country_id)
        # prevent name change if invoices exist
        if data.get('partner_id'):
            partner = request.env['res.partner'].browse(int(data['partner_id']))
            if partner.exists() and partner.name and \
                    not partner.sudo().can_edit_vat() and 'name' in data and (
                    data['name'] or False) != (partner.name or False):
                error['name'] = 'error'
                error_message.append(
                    _('Changing your name is not allowed once invoices '
                      'have been issued for your account. Please contact us '
                      'directly for this operation.'))
        # Required fields from form
        required_fields = [f for f in
                           (all_form_values.get('field_required') or '').split(
                               ',') if f]
        # Required fields from mandatory field function
        country_id = int(data.get('country_id', False))
        required_fields += mode[
                               1] == 'shipping' and \
                           self._get_mandatory_fields_shipping(country_id) or \
                           self._get_mandatory_fields_billing(country_id)
        if mode[1] == 'shipping':
            if not request.env['ir.config_parameter'].sudo().get_param(
                    'website_sale_address_management.'
                    'is_shipping_phone_is_required'):
                if 'phone' in required_fields:
                    required_fields.remove('phone')
            if not request.env['ir.config_parameter'].sudo().get_param(
                    'website_sale_address_management.'
                    'is_shipping_zip_code_is_required'):
                if 'zip' in required_fields:
                    required_fields.remove('zip')
            if not request.env['ir.config_parameter'].sudo().get_param(
                    'website_sale_address_management.'
                    'is_shipping_street_is_required'):
                if 'street' in required_fields:
                    required_fields.remove('street')
            if not request.env['ir.config_parameter'].sudo().get_param(
                    'website_sale_address_management.'
                    'is_shipping_city_is_required'):
                if 'city' in required_fields:
                    required_fields.remove('city')
        elif mode[1] == 'billing':
            if not request.env['ir.config_parameter'].sudo().get_param(
                    'website_sale_address_management.'
                    'is_billing_phone_is_required'):
                if 'phone' in required_fields:
                    required_fields.remove('phone')
            if not request.env['ir.config_parameter'].sudo().get_param(
                    'website_sale_address_management.'
                    'is_billing_zip_code_is_required'):
                if 'zip' in required_fields:
                    required_fields.remove('zip')
            if not request.env['ir.config_parameter'].sudo().get_param(
                    'website_sale_address_management.'
                    'is_billing_street_is_required'):
                if 'street' in required_fields:
                    required_fields.remove('street')
            if not request.env['ir.config_parameter'].sudo().get_param(
                    'website_sale_address_management.'
                    'is_billing_city_is_required'):
                if 'city' in required_fields:
                    required_fields.remove('city')
        # error message for empty required fields
        for field_name in required_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'
        # email validation
        if data.get('email') and not tools.single_email_re.match(
                data.get('email')):
            error["email"] = 'error'
            error_message.append(
                _('Invalid Email! Please enter a valid email address.'))
        # vat validation
        Partner = request.env['res.partner']
        if data.get("vat") and hasattr(Partner, "check_vat"):
            if country_id:
                data["vat"] = Partner.fix_eu_vat_number(country_id,
                                                        data.get("vat"))
            partner_dummy = Partner.new(self._get_vat_validation_fields(data))
            try:
                partner_dummy.check_vat()
            except ValidationError as exception:
                error["vat"] = 'error'
                error_message.append(exception.args[0])

        if [err for err in error.values() if err == 'missing']:
            error_message.append(_('Some required fields are empty.'))
        return error, error_message

    def _get_mandatory_fields_billing(self, country_id=False):
        """function to monkey patch function _get_mandatory_fields_billing and
            remove not required fields from list req"""
        req = ["name", "email", "street", "city", "country_id", "phone"]
        if country_id:
            country = request.env['res.country'].browse(country_id)
            if country.state_required:
                req += ['state_id']
            if country.zip_required:
                req += ['zip']
        if not request.env['ir.config_parameter'].sudo().get_param(
                'website_sale_address_management.'
                'is_billing_phone_is_required'):
            req.remove('phone')
        if not request.env['ir.config_parameter'].sudo().get_param(
                'website_sale_address_management.'
                'is_billing_zip_code_is_required'):
            if "zip" in req:
                req.remove('zip')
        if not request.env['ir.config_parameter'].sudo().get_param(
                'website_sale_address_management.'
                'is_billing_street_is_required'):
            req.remove('street')
        if not request.env['ir.config_parameter'].sudo().get_param(
                'website_sale_address_management.'
                'is_billing_city_is_required'):
            req.remove('city')
        return req

    def _get_mandatory_fields_shipping(self, country_id=False):
        """function to monkey patch function _get_mandatory_fields_shipping and
            remove not required fields from list req"""
        req = ["name", "street", "city", "country_id", "phone"]
        if country_id:
            country = request.env['res.country'].browse(country_id)
            if country.state_required:
                req += ['state_id']
            if country.zip_required:
                req += ['zip']
        if not request.env['ir.config_parameter'].sudo().get_param(
                'website_sale_address_management.'
                'is_shipping_phone_is_required'):
            req.remove('phone')
        if not request.env['ir.config_parameter'].sudo().get_param(
                'website_sale_address_management.'
                'is_shipping_zip_code_is_required'):
            if "zip" in req:
                req.remove('zip')
        if not request.env['ir.config_parameter'].sudo().get_param(
                'website_sale_address_management.'
                'is_shipping_street_is_required'):
            req.remove('street')
        if not request.env['ir.config_parameter'].sudo().get_param(
                'website_sale_address_management.'
                'is_shipping_city_is_required'):
            req.remove('city')
        return req

    WebsiteSale.checkout_form_validate = checkout_form_validate
    WebsiteSale._get_mandatory_fields_billing = _get_mandatory_fields_billing
    WebsiteSale._get_mandatory_fields_shipping = _get_mandatory_fields_shipping
