# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.http import request, route

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleL10nMX(WebsiteSale):

    def _l10n_mx_edi_is_extra_info_needed(self):
        order = request.website.sale_get_order()
        return order.company_id.country_code == 'MX'

    @route()
    def shop_checkout(self, try_skip_step=False, **query_params):
        # Extends 'website_sale'
        # Prevent express checkout
        if self._l10n_mx_edi_is_extra_info_needed() and try_skip_step:
            try_skip_step = False
        return super().shop_checkout(try_skip_step=try_skip_step, query_params=query_params)

    @route('/shop/l10n_mx_invoicing_info', type='http', auth='public', website=True, sitemap=False)
    def l10n_mx_invoicing_info(self, **kw):
        if not self._l10n_mx_edi_is_extra_info_needed():
            return request.redirect("/shop/confirm_order")

        order = request.website.sale_get_order()
        redirection = self._check_cart(order)
        if redirection:
            return redirection

        partner = order.partner_id

        l10n_mx_edi_fields = [
            request.env['ir.model.fields']._get('res.partner', 'l10n_mx_edi_fiscal_regime'),
            request.env['ir.model.fields']._get('account.move', 'l10n_mx_edi_usage'),
            request.env['ir.model.fields']._get('account.move', 'l10n_mx_edi_payment_method_id'),
            request.env['ir.model.fields']._get('res.partner', 'l10n_mx_edi_no_tax_breakdown'),
        ]

        # === GET ===
        default_vals = {}
        if request.httprequest.method == 'GET':
            default_vals['vat'] = partner.vat
            default_vals['need_invoice'] = not order.l10n_mx_edi_cfdi_to_public
            default_vals['l10n_mx_edi_fiscal_regime'] = partner.l10n_mx_edi_fiscal_regime
            default_vals['l10n_mx_edi_usage'] = order.l10n_mx_edi_usage
            default_vals['l10n_mx_edi_no_tax_breakdown'] = partner.l10n_mx_edi_no_tax_breakdown
            default_vals['l10n_mx_edi_payment_method_id'] = order.l10n_mx_edi_payment_method_id

        # === POST & possibly redirect ===
        can_edit_vat = partner.can_edit_vat()
        errors = {}
        if request.httprequest.method == 'POST':
            order.l10n_mx_edi_cfdi_to_public = kw.get('need_invoice') != '1'
            if kw.get('need_invoice') == '1':
                default_vals = {
                    'vat': kw.get('vat'),
                    'need_invoice': True,
                    'l10n_mx_edi_fiscal_regime': kw.get('l10n_mx_edi_fiscal_regime'),
                    'l10n_mx_edi_usage': kw.get('l10n_mx_edi_usage'),
                    'l10n_mx_edi_no_tax_breakdown': kw.get('l10n_mx_edi_no_tax_breakdown') == 'on',
                    'l10n_mx_edi_payment_method_id': int(kw.get('l10n_mx_edi_payment_method_id', False)) or False,
                }
                partner_vals = {}
                # VAT field
                if not default_vals['vat']:
                    errors['vat'] = _("The VAT number is required")
                elif can_edit_vat:
                    if request.env['res.partner']._run_vat_test(default_vals['vat'], partner.country_id, partner.is_company) is False:
                        errors['vat'] = partner._build_vat_error_message(partner.country_id.code.lower(), default_vals['vat'], partner.name)
                    else:
                        partner_vals['vat'] = default_vals['vat']
                # Other fields
                order.l10n_mx_edi_usage = default_vals['l10n_mx_edi_usage']
                order.l10n_mx_edi_payment_method_id = default_vals['l10n_mx_edi_payment_method_id']
                partner_vals.update({
                    'l10n_mx_edi_fiscal_regime': default_vals['l10n_mx_edi_fiscal_regime'],
                    'l10n_mx_edi_no_tax_breakdown': default_vals['l10n_mx_edi_no_tax_breakdown'],
                })
                partner.write(partner_vals)
                if not errors:
                    return request.redirect("/shop/confirm_order")
            else:
                return request.redirect("/shop/confirm_order")

        # === Render extra_info tab ===
        values = {
            'request': request,
            'website_sale_order': order,
            'post': kw,
            'partner': partner.id,
            'order': order,
            'l10n_mx_edi_fields': l10n_mx_edi_fields,
            'l10n_mx_edi_payment_methods': request.env['l10n_mx_edi.payment.method'].sudo().search([]),
            'company_country_code': order.company_id.country_id.code,
            'default_vals': default_vals,
            'errors': errors,
            # flag for rendering the 'Extra Info' dot in the wizard_checkout
            'l10n_mx_show_extra_info': True,
            'can_edit_vat': can_edit_vat,
        }
        return request.render("l10n_mx_edi_website_sale.l10n_mx_edi_invoicing_info", values)
