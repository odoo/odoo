# Part of Odoo. See LICENSE file for full copyright and licensing details.
from stdnum.cl import rut

from odoo import _, tools, http
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class L10nCLWebsiteSale(WebsiteSale):

    def _l10n_cl_is_extra_info_needed(self):
        order = request.website.sale_get_order()
        return order.company_id.country_code == 'CL' \
               and request.env['ir.config_parameter'].sudo().get_param('sale.automatic_invoice') == 'True'

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

    def _checkout_invoice_info_form_empty(self, **kw):
        return [key for key, value in kw.items() if value.strip() == '']

    def _checkout_invoice_info_form_validate(self, order, **kw):
        errors = {}
        if kw.get('vat') and not rut.is_valid(kw.get('vat').strip()):
            errors['vat'] = _('The RUT %s is not valid', kw.get('vat'))
        if kw.get('l10n_cl_type_document') == 'invoice' and order.partner_id.country_id.code != 'CL':
            errors['cl'] = _('You need to be a resident of Chile in order to request an invoice')
        if kw.get('l10n_cl_dte_email', '') and not tools.single_email_re.match(kw.get('l10n_cl_dte_email')):
            errors['dte_email'] = _('Invalid DTE email! Please enter a valid email address.')
        return errors

    def _get_default_value_invoice_info(self, order, **kw):
        return {
            'l10n_cl_type_document': kw.get('l10n_cl_type_document', 'ticket'),
            'l10n_cl_activity_description': kw.get('l10n_cl_activity_description', order.partner_id.l10n_cl_activity_description),
            'l10n_cl_dte_email': kw.get('l10n_cl_dte_email', ''),
            'vat': kw.get('vat') or order.partner_id.vat,
        }

    def _l10n_cl_update_order(self, order, **kw):
        if kw.get('l10n_cl_type_document') == 'ticket':
            order.partner_invoice_id = request.env.ref('l10n_cl.par_cfa')
        if kw.get('l10n_cl_type_document') == 'invoice':
            order.partner_id.l10n_cl_sii_taxpayer_type = '1'
            order.partner_id.l10n_cl_activity_description = kw.get('l10n_cl_activity_description')
            order.partner_id.vat = kw.get('vat')
            order.partner_id.l10n_cl_dte_email = kw.get('l10n_cl_dte_email')

    @http.route(['/shop/l10n_cl_invoicing_info'], type='http', auth="public", methods=['GET', 'POST'], website=True, sitemap=False)
    def l10n_cl_invoicing_info(self, **kw):
        order = request.website.sale_get_order()
        values = {
            'website_sale_order': order,
            'l10n_cl_show_extra_info': True,
            'default_value': kw,
            'errors_fields': self._checkout_invoice_info_form_validate(order, **kw),
            'errors_empty': self._checkout_invoice_info_form_empty(**kw),
        }
        if request.httprequest.method == 'POST':
            if (values['errors_fields'] or values['errors_empty']) and kw['l10n_cl_type_document'] != 'ticket':
                return request.render("l10n_cl_edi_website_sale.l10n_cl_edi_invoicing_info", values)
            self._l10n_cl_update_order(order, **kw)
            return request.redirect("/shop/confirm_order")
        # httprequest.method GET
        if order.partner_id.country_id.code != 'CL':
            order.partner_invoice_id = request.env.ref('l10n_cl.par_cfa')
            return request.redirect("/shop/confirm_order")
        if 'l10n_cl_type_document' not in values['default_value']:
            values['default_value'].update(l10n_cl_type_document='ticket')
        return request.render('l10n_cl_edi_website_sale.l10n_cl_edi_invoicing_info', values)

    def _check_billing_partner_mandatory_fields(self, partner):
        # In case of 'ticket' l10n_cl_document_type, the invoicing partner is a generic anonymous
        # one that cannot and shouldn't be edited by the customer.
        if partner.id == request.env['ir.model.data']._xmlid_to_res_id('l10n_cl.par_cfa'):
            return True
        return super()._check_billing_partner_mandatory_fields(partner)
