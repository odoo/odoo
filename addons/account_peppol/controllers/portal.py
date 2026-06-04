# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.http import request
from odoo.tools.partner_identifiers import validation_error_message

from odoo.addons.account.controllers.portal import PortalAccount as CustomerPortal
from odoo.addons.account.models.company import PEPPOL_LIST
from odoo.addons.account_edi_ubl_cii.tools.partner_identifiers import validate_participant_identifier


class PortalAccount(CustomerPortal):

    # ------------------------------------------------------------
    # My Account
    # ------------------------------------------------------------

    def _prepare_my_account_rendering_values(self, *args, **kwargs):
        rendering_values = super()._prepare_my_account_rendering_values(*args, **kwargs)
        if request.env.company.peppol_can_send:
            rendering_values['invoice_sending_methods'].update({'peppol': _("by Peppol")})
            rendering_values.update({
                'routing_scheme_list': dict(request.env['res.partner']._fields['routing_scheme'].selection),
            })
        return rendering_values

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
            result = validate_participant_identifier(peppol_eas, peppol_endpoint)
            if not result['valid']:
                invalid_fields.add('invalid_peppol_endpoint')
                peppol_endpoint = result['value']
                endpoint_error_message = validation_error_message(request.env, result['key'], result['example'])
                error_messages.append(endpoint_error_message)
            peppol_identifier = f'{peppol_eas}:{peppol_endpoint}'
            if request.env['res.partner']._get_peppol_verification_state(peppol_identifier, edi_format) != 'valid':
                invalid_fields.add('invalid_peppol_config')
                error_messages.append(_("If you want to be invoiced by Peppol, your configuration must be valid."))

        return invalid_fields, missing_fields, error_messages
