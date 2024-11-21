from base64 import b64encode
from odoo import api, models, _
from odoo.addons.account.models.company import PEPPOL_LIST
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _get_default_sending_methods(self, move) -> set:
        """ By default, we use the sending method set on the partner or email and peppol. """
        # OVERRIDE 'account'
        if invoice_sending_method := move.partner_id.with_company(move.company_id).invoice_sending_method:
            return {invoice_sending_method}

        if self._is_applicable_to_company('peppol', move.company_id):
            return {'email', 'peppol'}

        return {'email'}

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        if peppol_moves := moves.filtered(lambda m: 'peppol' in moves_data[m]['sending_methods']):
            invalid_partners = peppol_moves.filtered(
                lambda move: move.partner_id.commercial_partner_id.with_company(move.company_id).peppol_verification_state != 'valid'
            ).partner_id.commercial_partner_id
            ubl_warning_already_displayed = 'account_edi_ubl_cii_configure_partner' in alerts
            if invalid_partners and not ubl_warning_already_displayed:
                alerts['account_peppol_warning_partner'] = {
                    'message': _("The following partners are not correctly configured to receive Peppol documents. "
                                 "Please check and verify their Peppol endpoint and the Electronic Invoicing format"),
                    'action_text': _("View Partner(s)"),
                    'action': invalid_partners._get_records_action(name=_("Check Partner(s)")),
                }
            edi_modes = [move.company_id.account_edi_proxy_client_ids.filtered(lambda usr: usr.proxy_type == 'peppol').edi_mode for move in peppol_moves]
            if any(edi_mode in ('test', 'demo') for edi_mode in edi_modes):
                alerts['account_peppol_demo_test_mode'] = {
                    'message': _("Peppol is in testing/demo mode."),
                    'level': 'info',
                }
        return alerts

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    def _get_mail_layout(self):
        # OVERRIDE 'account'
        return 'account_peppol.mail_notification_layout_with_responsible_signature_and_peppol'

    def _do_peppol_pre_send(self, moves):
        if len(moves.company_id) == 1:
            can_send = self.env['account_edi_proxy_client.user']._get_can_send_domain()
            if moves.company_id.account_peppol_proxy_state not in can_send:
                registration_wizard = self.env['peppol.registration'].create({'company_id': moves.company_id.id})
                return registration_wizard._action_open_peppol_form(reopen=False)

        for move in moves:
            if move.peppol_move_state in ('ready', False):
                move.peppol_move_state = 'to_send'

    def _is_applicable_to_company(self, method, company):
        # EXTENDS 'account'
        if method == 'peppol':
            return company.country_code in PEPPOL_LIST and company.account_peppol_proxy_state != 'rejected'
        else:
            return super()._is_applicable_to_company(method, company)

    def _is_applicable_to_move(self, method, move):
        # EXTENDS 'account'
        if method == 'peppol':
            return all([
                self._is_applicable_to_company(method, move.company_id),
                move.partner_id.commercial_partner_id.with_company(move.company_id).is_peppol_edi_format,
                move.company_id.account_peppol_proxy_state != 'rejected',
                move._need_ubl_cii_xml(move.partner_id.commercial_partner_id.with_company(move.company_id).invoice_edi_format)
                or move.ubl_cii_xml_id and move.peppol_move_state not in ('processing', 'done'),
            ])
        else:
            return super()._is_applicable_to_move(method, move)

    def _hook_if_errors(self, moves_data, allow_raising=True):
        # EXTENDS 'account'
        # to update `peppol_move_state` as `skipped` to show users that something went wrong
        # because those moves that failed XML/PDF files generation are not sent via Peppol
        moves_failed_file_generation = self.env['account.move']
        for move, move_data in moves_data.items():
            if 'peppol' in move_data['sending_methods'] and move_data.get('blocking_error'):
                moves_failed_file_generation |= move

        moves_failed_file_generation.peppol_move_state = 'skipped'

        return super()._hook_if_errors(moves_data, allow_raising=allow_raising)

    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)

        params = {'documents': []}
        invoices_data_peppol = {}
        for invoice, invoice_data in invoices_data.items():
            if 'peppol' in invoice_data['sending_methods'] and self._is_applicable_to_move('peppol', invoice):
                if invoice_data.get('ubl_cii_xml_attachment_values'):
                    xml_file = invoice_data['ubl_cii_xml_attachment_values']['raw']
                    filename = invoice_data['ubl_cii_xml_attachment_values']['name']
                elif invoice.ubl_cii_xml_id and invoice.peppol_move_state not in ('processing', 'done'):
                    xml_file = invoice.ubl_cii_xml_id.raw
                    filename = invoice.ubl_cii_xml_id.name
                else:
                    invoice.peppol_move_state = 'skipped'
                    continue

                partner = invoice.partner_id.commercial_partner_id.with_company(invoice.company_id)
                if not partner.peppol_eas or not partner.peppol_endpoint:
                    invoice.peppol_move_state = 'error'
                    invoice_data['error'] = _('The partner is missing Peppol EAS and/or Endpoint identifier.')
                    continue

                if partner.peppol_verification_state != 'valid':
                    invoice.peppol_move_state = 'error'
                    invoice_data['error'] = _('Please verify partner configuration in partner settings.')
                    continue

                receiver_identification = f"{partner.peppol_eas}:{partner.peppol_endpoint}"
                params['documents'].append({
                    'filename': filename,
                    'receiver': receiver_identification,
                    'ubl': b64encode(xml_file).decode(),
                })
                invoices_data_peppol[invoice] = invoice_data

        if not params['documents']:
            return

        edi_user = next(iter(invoices_data)).company_id.account_edi_proxy_client_ids.filtered(
            lambda u: u.proxy_type == 'peppol')

        try:
            response = edi_user._make_request(
                f"{edi_user._get_server_url()}/api/peppol/1/send_document",
                params=params,
            )
        except AccountEdiProxyError as e:
            for invoice, invoice_data in invoices_data_peppol.items():
                invoice.peppol_move_state = 'error'
                invoice_data['error'] = e.message
        else:
            if response.get('error'):
                # at the moment the only error that can happen here is ParticipantNotReady error
                for invoice, invoice_data in invoices_data_peppol.items():
                    invoice.peppol_move_state = 'error'
                    invoice_data['error'] = response['error']['message']
            else:
                # the response only contains message uuids,
                # so we have to rely on the order to connect peppol messages to account.move
                invoices = self.env['account.move']
                for message, (invoice, _invoice_data) in zip(response['messages'], invoices_data_peppol.items()):
                    invoice.peppol_message_uuid = message['message_uuid']
                    invoice.peppol_move_state = 'processing'
                    invoices |= invoice
                log_message = _('The document has been sent to the Peppol Access Point for processing')
                invoices._message_log_batch(bodies={invoice.id: log_message for invoice in invoices})

        if self._can_commit():
            self._cr.commit()
