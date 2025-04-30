# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.http import request

from odoo.addons.account.controllers.portal import PortalAccount as CustomerPortal
from odoo.addons.account.models.company import PEPPOL_LIST


class PortalAccount(CustomerPortal):

    # ------------------------------------------------------------
    # My Account
    # ------------------------------------------------------------

    def _prepare_my_account_rendering_values(self, *args, **kwargs):
        rendering_values = super()._prepare_my_account_rendering_values(*args, **kwargs)
        if request.env.company.peppol_can_send:
            rendering_values['invoice_sending_methods'].update({'peppol': _("by Peppol")})
            rendering_values.update({
                'peppol_eas_list': dict(request.env['res.partner']._fields['peppol_eas'].selection),
            })
        return rendering_values

    def _get_mandatory_billing_address_fields(self, country_sudo):
        mandatory_fields = super()._get_mandatory_billing_address_fields(country_sudo)

        sending_method = request.params.get('invoice_sending_method')
        if sending_method == 'peppol':
            mandatory_fields.update({'peppol_eas', 'peppol_endpoint', 'invoice_edi_format'})

        return mandatory_fields

    def _validate_address_values(self, address_values, *args, **kwargs):
        # EXTENDS 'portal'
        invalid_fields, missing_fields, error_messages = super()._validate_address_values(
            address_values, *args, **kwargs
        )

        if address_values.get('invoice_sending_method') == 'peppol':
            peppol_eas = address_values.get('peppol_eas')
            peppol_endpoint = address_values.get('peppol_endpoint')
            edi_format = address_values.get('invoice_edi_format')
            if request.env['res.country'].browse(int(address_values.get('country_id'))).code not in PEPPOL_LIST:
                invalid_fields.add('country_id')
                address_values['country_id'] = 'error'
                error_messages.append(_("That country is not available for Peppol."))
            if endpoint_error_message := request.env['res.partner']._build_error_peppol_endpoint(peppol_eas, peppol_endpoint):
                invalid_fields.add('invalid_peppol_endpoint')
                error_messages.append(endpoint_error_message)
            if request.env['res.partner']._get_peppol_verification_state(peppol_endpoint, peppol_eas, edi_format) != 'valid':
                invalid_fields.add('invalid_peppol_config')
                error_messages.append(_("If you want to be invoiced by Peppol, your configuration must be valid."))

        return invalid_fields, missing_fields, error_messages
