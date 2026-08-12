# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.http import request
from odoo.tools.partner_identifiers import validation_error_message

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
                'routing_scheme_list': dict(request.env['res.partner']._fields['routing_scheme']._description_selection(request.env)),
            })
        return rendering_values

    def _validate_address_values(self, address_values, *args, **kwargs):
        # EXTENDS 'portal'
        invalid_fields, missing_fields, error_messages = super()._validate_address_values(
            address_values, *args, **kwargs
        )

        if address_values.get('invoice_sending_method') == 'peppol':
            routing_scheme = address_values.get('routing_scheme')
            routing_endpoint = address_values.get('routing_endpoint')
            edi_format = address_values.get('invoice_edi_format')
            if request.env['res.country'].browse(int(address_values.get('country_id'))).code not in PEPPOL_LIST:
                invalid_fields.add('country_id')
                error_messages.append(_("That country is not available for Peppol."))
                return invalid_fields, missing_fields, error_messages
            error_message = self.env._("If you want to be invoiced by Peppol, your configuration must be valid.")
            if not routing_scheme or not routing_endpoint or not edi_format:
                if not routing_scheme:
                    missing_fields.add('routing_scheme')
                if not routing_endpoint:
                    missing_fields.add('routing_endpoint')
                if not edi_format:
                    missing_fields.add('invoice_edi_format')
                error_messages.append(error_message)
                return invalid_fields, missing_fields, error_messages
            result = request.env['res.partner']._validate_identifier_by_scheme(routing_scheme, routing_endpoint)
            if not result['valid']:
                invalid_fields.add('routing_endpoint')
                routing_endpoint = result['value']
                identifier_label = request.env['res.partner']._get_identifier_label(result['key'])
                endpoint_error_message = validation_error_message(request.env, identifier_label, result['value'], example=result['example'])
                error_messages.append(endpoint_error_message)
            routing_identifier = f'{routing_scheme}:{routing_endpoint}'
            if request.env['res.partner']._get_peppol_verification_state(routing_identifier, edi_format) != 'valid':
                invalid_fields.update({'routing_scheme', 'routing_endpoint', 'invoice_edi_format'})
                error_messages.append(error_message)

        return invalid_fields, missing_fields, error_messages
