from odoo.addons.account.controllers.portal import CustomerPortal
from odoo.http import request


class CustomerPortalInherit(CustomerPortal):

    def details_form_validate(self, data, partner_creation=False):
        error, error_message = super().details_form_validate(data, partner_creation)
        if country_id := request.params.get('country_id'):
            country = request.env['res.country'].search([('id', '=', country_id)], limit=1)
        else:
            country = request.env['res.country'].browse()
        if (
            request.env.company.account_fiscal_country_id.code == "IN"
            and country.code == "IN"
            and (vat := data.get('vat')) and vat != request.env.user.partner_id.vat
        ):
            request.env.user.partner_id.sudo().action_l10n_in_verify_gstin_status(vat=vat, ignore_errors=True)
        return error, error_message
