from base64 import b64encode
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_fr_pdp.models.account_move import UNSENT_PDP_MOVE_STATES


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _get_default_sending_method(self, move) -> str:
        # EXTENDS 'account'
        preferred_method = move.commercial_partner_id.with_company(move.company_id).invoice_sending_method
        if not preferred_method and self._is_applicable_to_move('pdp', move):
            return 'pdp'
        return super()._get_default_sending_method(move)

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    def _get_default_invoice_edi_format(self, move, **kwargs) -> str:
        # EXTENDS 'account'
        if 'pdp' in kwargs.get('sending_methods', []):
            proxy_type = move.partner_id._get_pdp_receiver_identification_info()[0]
            return 'ubl_21_fr' if proxy_type == 'pdp' else move.partner_id.with_company(move.company_id)._get_peppol_edi_format()
        return super()._get_default_invoice_edi_format(move, **kwargs)

    def _is_applicable_to_company(self, method, company):
        # EXTENDS 'account'
        if method != 'pdp':
            return super()._is_applicable_to_company(method, company)
        return company.l10n_fr_pdp_proxy_state == 'receiver'

    def _is_applicable_to_move(self, method, move, **move_data):
        # EXTENDS 'account'
        if method != 'pdp':
            return super()._is_applicable_to_move(method, move, **move_data)

        partner = move.partner_id.commercial_partner_id.with_company(move.company_id)
        invoice_edi_format = move_data.get('invoice_edi_format') or 'ubl_21_fr'
        return all([
            self._is_applicable_to_company(method, move.company_id),
            partner._get_pdp_verification_state(invoice_edi_format) == 'valid',
            move._need_ubl_cii_xml(invoice_edi_format)
            or move.ubl_cii_xml_id and move.pdp_move_state in UNSENT_PDP_MOVE_STATES,
        ])

    def _hook_if_errors(self, moves_data, allow_raising=True):
        # EXTENDS 'account'
        # to update `pdp_move_state` as `error` to show users that something went wrong
        # because those moves that failed XML/PDF files generation are not sent via PDP
        moves_failed_file_generation = self.env['account.move']
        for move, move_data in moves_data.items():
            if 'pdp' in move_data['sending_methods'] and move_data.get('blocking_error'):
                moves_failed_file_generation |= move

        moves_failed_file_generation.pdp_move_state = 'error'

        return super()._hook_if_errors(moves_data, allow_raising=allow_raising)

    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)

        params = {'documents': []}
        invoices_data_pdp = {}
        for invoice, invoice_data in invoices_data.items():
            partner = invoice.partner_id.commercial_partner_id.with_company(invoice.company_id)
            if 'pdp' not in invoice_data['sending_methods']:
                continue

            if not partner._get_pdp_receiver_identification_info():
                invoice.pdp_move_state = 'error'
                invoice_data['error'] = _('The partner is missing the receiver identification (PDP Identifier or Peppol EAS & Endpoint)')
                continue

            if partner._get_pdp_verification_state(invoice_data['invoice_edi_format']) != 'valid':
                invoice.pdp_move_state = 'error'
                invoice_data['error'] = _('Please verify partner configuration in partner settings.')
                continue

            if not self._is_applicable_to_move('pdp', invoice, **invoice_data):
                continue

            if invoice_data.get('ubl_cii_xml_attachment_values'):
                xml_file = invoice_data['ubl_cii_xml_attachment_values']['raw']
                filename = invoice_data['ubl_cii_xml_attachment_values']['name']
            elif invoice.ubl_cii_xml_id and invoice.pdp_move_state in UNSENT_PDP_MOVE_STATES:
                xml_file = invoice.ubl_cii_xml_id.raw
                filename = invoice.ubl_cii_xml_id.name
            else:
                invoice.pdp_move_state = 'error'
                builder = invoice.partner_id.commercial_partner_id._get_edi_builder(invoice_data['invoice_edi_format'])
                invoice_data['error'] = _(
                    "Errors occurred while creating the EDI document (format: %s):",
                    builder._description,
                )
                continue

            # There is a check on IAP that the reciever info in the XML matches the receiver info
            # in the AS4 envelope (so we do not check whether the XML actually uses `receiver_identification`).
            receiver_identification = partner._get_pdp_receiver_identification_info()[1]
            params['documents'].append({
                'filename': filename,
                'receiver': receiver_identification,
                'ubl': b64encode(xml_file).decode(),
                'flow_number': 2,  # We also send "nromal" Peppol messages here; IAP server decides what to do.
            })
            invoices_data_pdp[invoice] = invoice_data

        if not params['documents']:
            return

        edi_user = next(iter(invoices_data)).company_id.pdp_edi_user

        try:
            response = edi_user._call_pdp_proxy(
                "/api/pdp/1/send_document",
                params=params,
            )
        except UserError as e:
            for invoice, invoice_data in invoices_data_pdp.items():
                invoice.pdp_move_state = 'error'
                invoice_data['error'] = str(e)
        else:
            if response.get('error'):
                # at the moment the only error that can happen here is ParticipantNotReady error
                for invoice, invoice_data in invoices_data_pdp.items():
                    invoice.pdp_move_state = 'error'
                    invoice_data['error'] = response['error']['message']
            else:
                # the response only contains message uuids,
                # so we have to rely on the order to connect pdp messages to account.move
                invoices = self.env['account.move']
                for message, (invoice, invoice_data) in zip(response['messages'], invoices_data_pdp.items()):
                    invoice.pdp_message_uuid = message['message_uuid']
                    invoice.pdp_move_state = 'processing'
                    invoices |= invoice
                log_message = _('The document has been sent to the PDP Access Point for processing')
                invoices._message_log_batch(bodies={invoice.id: log_message for invoice in invoices})
                self.env.ref('l10n_fr_pdp.ir_cron_pdp_get_message_status')._trigger(at=fields.Datetime.now() + timedelta(minutes=5))

        if self._can_commit():
            self._cr.commit()
