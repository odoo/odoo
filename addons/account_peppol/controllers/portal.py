from odoo import _
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.account.models.company import PEPPOL_LIST
from odoo.http import request


class PortalAccount(CustomerPortal):

    # ------------------------------------------------------------
    # My Account
    # ------------------------------------------------------------

    def _prepare_portal_layout_values(self):
        # EXTENDS 'portal'
        portal_layout_values = super()._prepare_portal_layout_values()
        can_send = request.env['account_edi_proxy_client.user']._get_can_send_domain()
        if request.env.company.account_peppol_proxy_state in can_send:
            partner = request.env.user.partner_id
            portal_layout_values['invoice_sending_methods'].update({'peppol': _('by Peppol')})
            portal_layout_values.update({
                'peppol_eas_list': dict(partner._fields['peppol_eas'].selection),
            })
        return portal_layout_values

    def _get_mandatory_fields(self):
        # EXTENDS 'portal'
        mandatory_fields = super()._get_mandatory_fields()

        sending_method = request.params.get('invoice_sending_method')
        if sending_method == 'peppol':
            mandatory_fields += ['peppol_eas', 'peppol_endpoint', 'invoice_edi_format']

        return mandatory_fields

    def _get_optional_fields(self):
        # EXTENDS 'portal'
        optional_fields = super()._get_optional_fields()

        sending_method = request.params.get('invoice_sending_method')
        if sending_method and sending_method != 'peppol':
            optional_fields += ['peppol_eas', 'peppol_endpoint']
        return optional_fields

    def details_form_validate(self, data, partner_creation=False):
        # EXTENDS 'portal'
        error, error_message = super().details_form_validate(data, partner_creation=False)

        if data.get('invoice_sending_method') == 'peppol':
            peppol_eas = data.get('peppol_eas')
            peppol_endpoint = data.get('peppol_endpoint')
            edi_format = data.get('invoice_edi_format')
            if request.env['res.country'].browse(int(data.get('country_id'))).code not in PEPPOL_LIST:
                error['country_id'] = 'error'
                error_message.append(_('That country is not available for Peppol.'))
            if endpoint_error_message := request.env['res.partner']._build_error_peppol_endpoint(peppol_eas, peppol_endpoint):
                error['invalid_peppol_endpoint'] = 'error'
                error_message.append(endpoint_error_message)
            if request.env['res.partner']._get_peppol_verification_state(peppol_endpoint, peppol_eas, edi_format) != 'valid':
                error['invalid_peppol_config'] = 'error'
                error_message.append(_('If you want to be invoiced by Peppol, your configuration must be valid.'))

        return error, error_message
