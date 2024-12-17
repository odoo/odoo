# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import werkzeug


from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request, route

from odoo.addons.l10n_tw_edi_ecpay.utils import call_ecpay_api
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleL10nTW(WebsiteSale):
    def _is_valid_mobile_barcode(self, carrier_number, order):
        json_data = {
            "MerchantID": order.company_id.l10n_tw_edi_ecpay_merchant_id,
            "BarCode": carrier_number,
        }

        response_data = call_ecpay_api("/CheckBarcode", json_data, order.company_id)
        return response_data.get("RtnCode") == 1 and response_data.get("IsExist") == "Y"

    def _is_valid_tax_id(self, tax_id, order):
        json_data = {
            "MerchantID": order.company_id.l10n_tw_edi_ecpay_merchant_id,
            "UnifiedBusinessNo": tax_id,
        }

        response_data = call_ecpay_api("/GetCompanyNameByTaxID", json_data, order.company_id)
        return response_data.get("RtnCode") == 1 and response_data.get("CompanyName")

    def _is_valid_love_code(self, love_code, order):
        json_data = {
            "MerchantID": order.company_id.l10n_tw_edi_ecpay_merchant_id,
            "LoveCode": love_code,
        }

        response_data = call_ecpay_api("/CheckLoveCode", json_data, order.company_id)
        return response_data.get("RtnCode") == 1 and response_data.get("IsExist") == "Y"

    def _get_render_context(self, order, default_vals, errors=None):
        carrier_field = request.env['sale.order']._fields['l10n_tw_edi_carrier_type']
        carrier_choices = [('0', '')] + carrier_field.selection
        return {
            'request': request,
            'website_sale_order': order,
            'l10n_tw_show_extra_info': True,
            'default_vals': default_vals,
            'errors': errors or {},
            'carrier_choices': carrier_choices,
            'post_url': '/shop/l10n_tw_invoicing_info/submit',
        }

    @route('/shop/l10n_tw_invoicing_info', type='http', auth='public', methods=['GET'], website=True, sitemap=False)
    def l10n_tw_invoicing_info_get(self, **kw):
        order = request.website.sale_get_order()
        default_vals = {
            'is_donate': "on" if order.l10n_tw_edi_love_code else False,
            'love_code': order.l10n_tw_edi_love_code,
            'carrier_type': order.l10n_tw_edi_carrier_type if order.l10n_tw_edi_carrier_type else "1",
            'carrier_number': order.l10n_tw_edi_carrier_number,
            'carrier_number_2': order.l10n_tw_edi_carrier_number_2,
        }
        values = self._get_render_context(order, default_vals)
        return request.render('l10n_tw_edi_ecpay_website_sale.l10n_tw_edi_invoicing_info', values)

    @route('/shop/l10n_tw_invoicing_info/submit', type='http', auth='public', methods=['POST'], website=True, sitemap=False)
    def l10n_tw_invoicing_info_post(self, **kw):
        order = request.website.sale_get_order()
        errors = {}
        default_vals = {
            'love_code': kw.get('l10n_tw_edi_love_code'),
            'carrier_type': kw.get('l10n_tw_edi_carrier_type'),
            'carrier_number': kw.get('l10n_tw_edi_carrier_number'),
            'carrier_number_2': kw.get('l10n_tw_edi_carrier_number_2'),
            'is_donate': kw.get('l10n_tw_edi_is_donate'),
        }
        if kw.get('l10n_tw_edi_is_donate') != 'on':
            if kw.get('l10n_tw_edi_carrier_type') == '2' and not kw.get('l10n_tw_edi_carrier_number'):
                errors['carrier_number'] = request.env._('Please enter the carrier number')
            if kw.get('l10n_tw_edi_carrier_type') == '3' \
                    and not self._is_valid_mobile_barcode(kw.get('l10n_tw_edi_carrier_number'), order):
                errors['carrier_number'] = request.env._('Mobile Barcode is invalid')
            if kw.get('l10n_tw_edi_carrier_type') in ['4', '5'] and (not kw.get('l10n_tw_edi_carrier_number') or not kw.get('l10n_tw_edi_carrier_number_2')):
                errors['carrier_number'] = request.env._('Please enter the carrier number and carrier number 2')
        elif kw.get('l10n_tw_edi_is_donate') == 'on' and not self._is_valid_love_code(kw.get('l10n_tw_edi_love_code'), order):
            errors['love_code'] = request.env._('Love Code is invalid')

        vals_to_write = {
            'l10n_tw_edi_is_print': False,
            'l10n_tw_edi_love_code': False,
            'l10n_tw_edi_carrier_type': False,
            'l10n_tw_edi_carrier_number': False,
            'l10n_tw_edi_carrier_number_2': False,
        }

        is_donate = default_vals.get('is_donate') == 'on'

        if is_donate and 'love_code' not in errors:
            vals_to_write['l10n_tw_edi_love_code'] = default_vals.get('love_code')

        if not is_donate and 'carrier_number' not in errors:
            carrier_type = default_vals.get('carrier_type')

            if carrier_type != '0':
                vals_to_write['l10n_tw_edi_carrier_type'] = carrier_type

            if carrier_type in ['2', '3', '4', '5']:
                vals_to_write['l10n_tw_edi_carrier_number'] = default_vals.get('carrier_number')

            if carrier_type in ['4', '5']:
                vals_to_write['l10n_tw_edi_carrier_number_2'] = default_vals.get('carrier_number_2')

        order.write(vals_to_write)

        if not errors:
            return request.redirect("/shop/confirm_order")

        values = self._get_render_context(order, default_vals, errors)
        return request.render('l10n_tw_edi_ecpay_website_sale.l10n_tw_edi_invoicing_info', values)

    @http.route("/payment/ecpay/check_mobile_barcode/<int:sale_order_id>", type="json", auth="public")
    def check_mobile_barcode(self, sale_order_id, **kwargs):
        try:
            order = CustomerPortal._document_check_access(self, 'sale.order', sale_order_id, kwargs.get("access_token"))
        except (AccessError, MissingError):
            raise werkzeug.exceptions.NotFound

        return self._is_valid_mobile_barcode(kwargs.get("carrier_number", False), order)

    @http.route("/payment/ecpay/check_love_code/<int:sale_order_id>", type="json", auth="public")
    def check_love_code(self, sale_order_id, **kwargs):
        try:
            order = CustomerPortal._document_check_access(self, 'sale.order', sale_order_id, kwargs.get("access_token"))
        except (AccessError, MissingError):
            raise werkzeug.exceptions.NotFound
        return self._is_valid_love_code(kwargs.get("love_code", False), order)

    def _prepare_address_form_values(self, order_sudo, partner_sudo, address_type, **kwargs):
        rendering_values = super()._prepare_address_form_values(
            order_sudo, partner_sudo, address_type=address_type, **kwargs
        )
        rendering_values["l10n_tw_edi_require_paper_format"] = partner_sudo.l10n_tw_edi_require_paper_format
        return rendering_values

    def _validate_address_values(self, address_values, partner_sudo, address_type, *args, **kwargs):
        invalid_fields, missing_fields, error_messages = super()._validate_address_values(
            address_values, partner_sudo, address_type, *args, **kwargs
        )

        if address_type == 'billing' and request.website.company_id.country_id.code == 'TW' and request.website.company_id._is_ecpay_enabled():
            phone = address_values.get('phone')
            if phone:
                formatted_phone = request.env['account.move']._reformat_phone_number(phone)
                if not re.fullmatch(r'[\d]+', formatted_phone):
                    error_messages.append(request.env._("Phone number contains invalid characters! It should be in the format: '+886 0997624293'."))
            if address_values.get('company_name'):  # B2B customer
                if not address_values.get('vat'):
                    missing_fields.add('vat')
                if not self._is_valid_tax_id(address_values.get('vat'), request.website.sale_get_order()):
                    invalid_fields.add('vat')
                    error_messages.append(request.env._("Please enter a valid Tax ID"))

        return invalid_fields, missing_fields, error_messages

    def _handle_extra_form_data(self, extra_form_data, address_values):
        super()._handle_extra_form_data(extra_form_data, address_values)

        if request.website.company_id.country_id.code == 'TW' and request.website.company_id._is_ecpay_enabled():
            order = request.website.sale_get_order()
            if address_values.get('company_name'):
                l10n_tw_edi_is_print = True
            else:
                l10n_tw_edi_is_print = extra_form_data.get('l10n_tw_edi_require_paper_format') == "1"
            if address_values.get('company_name'):  # B2B customer
                # Create company contact if it does not exist
                if not order.partner_id.parent_id:
                    company_contact = request.env['res.partner'].sudo().create({
                        'name': address_values.get('company_name'),
                        'vat': address_values.get('vat'),
                        'company_type': 'company',
                        'l10n_tw_edi_require_paper_format': l10n_tw_edi_is_print,
                    })
                    order.partner_id.parent_id = company_contact
                else:
                    order.partner_id.parent_id.write({
                        'name': address_values.get('company_name'),
                        'vat': address_values.get('vat'),
                        'l10n_tw_edi_require_paper_format': l10n_tw_edi_is_print,
                    })
            else:  # B2C customer
                order.partner_id.l10n_tw_edi_require_paper_format = l10n_tw_edi_is_print

            order.l10n_tw_edi_is_print = l10n_tw_edi_is_print
