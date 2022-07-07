# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request
from odoo import http
from stdnum.cl import rut


class L10nCLWebsiteSale(WebsiteSale):

    @staticmethod
    def _l10n_cl_is_extra_info_needed():
        order = request.website.sale_get_order()
        return order.company_id.country_code == 'CL' \
               and request.env['ir.config_parameter'].sudo().get_param('sale.automatic_invoice') == 'True'

    def _cart_values(self, **kw):
        # OVERRIDE: Add flag in cart template (step 10)
        res = super()._cart_values(**kw)
        res['l10n_cl_show_extra_info'] = self._l10n_cl_is_extra_info_needed()
        return res

    def _get_country_related_render_values(self, kw, render_values):
        # OVERRIDE: Add flag in address template (step 20)
        vals = super()._get_country_related_render_values(kw, render_values)
        vals['l10n_cl_show_extra_info'] = self._l10n_cl_is_extra_info_needed()
        return vals

    def checkout_values(self, **kw):
        # OVERRIDE: Add flag in checkout template (step 20, when address is filled)
        vals = super().checkout_values(**kw)
        vals['l10n_cl_show_extra_info'] = self._l10n_cl_is_extra_info_needed()
        return vals

    def _extra_info_values(self, **kw):
        # OVERRIDE: Add flag in extra info template (step 30)
        return {'l10n_cl_show_extra_info': self._l10n_cl_is_extra_info_needed()}

    def _get_shop_payment_values(self, order, **kwargs):
        # OVERRIDE: Add flag in payment template (step 40)
        vals = super()._get_shop_payment_values(order, **kwargs)
        vals['l10n_cl_show_extra_info'] = self._l10n_cl_is_extra_info_needed()
        return vals

    @http.route()
    def address(self, **kw):
        if self._l10n_cl_is_extra_info_needed():
            kw['callback'] = "/shop/l10n_cl_invoicing_info"
        return super().address(**kw)

    @http.route()
    def checkout(self, **kw):
        if self._l10n_cl_is_extra_info_needed() and kw.get('express'):
            kw.pop('express')
        return super().checkout(**kw)

    @staticmethod
    def _checkout_invoice_info_form_empty(**kw):
        return [key for key, value in kw.items() if value.strip() == '']

    def _checkout_invoice_info_form_validate(self, order, **kw):
        errors = {}
        if kw.get('vat') and not rut.is_valid(kw.get('vat').strip()):
            errors['vat'] = _('Format VAT {} is not valid'.format(kw.get('vat')))
        if kw.get('l10n_cl_type_document') == 'invoice' and order.partner_id.country_id.code != 'CL':
            errors['cl'] = _('This option is not valid by localitation {}'.format(order.partner_id.country_id.name))
        return errors

    def _get_default_value_invoice_info(self, order, **kw):
        return {
            'l10n_cl_type_document': kw.get('l10n_cl_type_document', 'ticket'),
            'l10n_cl_activity_description': kw.get('l10n_cl_activity_description') or order.partner_id.l10n_cl_activity_description,
            'vat': kw.get('vat') or order.partner_id.vat,
        }

    def _l10n_cl_update_order(self, order, **kw):
        if kw.get('l10n_cl_type_document') == 'ticket':
            order.partner_invoice_id = request.env.ref('l10n_cl.par_cfa')
        if kw.get('l10n_cl_type_document') == 'invoice':
            order.partner_id.l10n_cl_sii_taxpayer_type = '1'
            order.partner_id.l10n_cl_activity_description = kw.get('l10n_cl_activity_description')
            order.partner_id.vat = kw.get('vat')

    @http.route(['/shop/l10n_cl_invoicing_info'], type='http', auth="public", methods=['GET', 'POST'], website=True, sitemap=False)
    def l10n_cl_invoicing_info(self, **kw):
        order = request.website.sale_get_order()
        default_value = self._get_default_value_invoice_info(order, **kw)
        values = {
            'website_sale_order': order,
            'l10n_cl_show_extra_info':True,
            'default_value': default_value,
            'errors_fields': self._checkout_invoice_info_form_validate(order, **kw),
            'errors_empty':self._checkout_invoice_info_form_empty(**kw)
        }
        if (values.get('errors_fields', False) or values.get('errors_empty', False)) and kw.get('l10n_cl_type_document') != 'ticket':
            return request.render("l10n_cl_website_sale.l10n_cl_edi_invoicing_info", values)
        if request.httprequest.method == 'POST':
            self._l10n_cl_update_order(order, **kw)
            return request.redirect("/shop/confirm_order")
        return request.render('l10n_cl_website_sale.l10n_cl_edi_invoicing_info', values)
