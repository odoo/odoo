from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class WebsiteSaleInherit(WebsiteSale):

    def shop_address_submit(
        self, partner_id=None, address_type='billing', use_delivery_as_billing=None,
        callback=None, required_fields=None, **form_data
    ):
        response = super().shop_address_submit(
            partner_id, address_type, use_delivery_as_billing, callback, required_fields, **form_data
        )
        if country_id := request.params.get('country_id'):
            country = request.env['res.country'].search([('id', '=', country_id)], limit=1)
        else:
            country = request.env['res.country'].browse()
        if (
            request.env.company.account_fiscal_country_id.code == "IN"
            and country.code == "IN"
            and request.params.get('vat') and request.params.get('vat') != request.env.user.partner_id.vat
        ):
            request.env.user.partner_id.sudo().action_l10n_in_verify_gstin_status(ignore_errors=True)
        return response
