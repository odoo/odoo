from base64 import b64encode
from datetime import timedelta

from odoo import _, fields, models
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    def _get_default_invoice_edi_format(self, move, **kwargs) -> str:
        # EXTENDS 'account'
        if 'eracun' in kwargs.get('sending_methods', []):
            return 'ubl_hr'

        return super()._get_default_invoice_edi_format(move, **kwargs)

    def _is_applicable_to_company(self, method, company):
        # EXTENDS 'account'
        if method == 'eracun':
            return company.l10n_hr_eracun_proxy_state != 'rejected'
        return super()._is_applicable_to_company(method, company)

    def _is_applicable_to_move(self, method, move, **move_data):
        # EXTENDS 'account'
        if method == 'eracun':
            partner = move.partner_id.commercial_partner_id.with_company(move.company_id)
            invoice_edi_format = move_data.get('invoice_edi_format') or 'ubl_hr'
            return all([
                self._is_applicable_to_company(method, move.company_id),
                partner._get_eracun_verification_state(invoice_edi_format) == 'valid',
                move.company_id.l10n_hr_eracun_proxy_state != 'rejected',
                move._need_ubl_cii_xml(invoice_edi_format)
                or move.ubl_cii_xml_id and move.eracun_move_state not in {'processing', 'done'},
            ])

        return super()._is_applicable_to_move(method, move, **move_data)

    def _hook_if_errors(self, moves_data, allow_raising=True):
        # EXTENDS 'account'
        moves_failed_file_generation = self.env['account.move']
        for move, move_data in moves_data.items():
            if 'eracun' in move_data['sending_methods'] and move_data.get('blocking_error'):
                moves_failed_file_generation |= move

        moves_failed_file_generation.eracun_move_state = 'error'

        return super()._hook_if_errors(moves_data, allow_raising=allow_raising)

    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)

        params = {'documents': []}
        invoices_data_eracun = {}
        for invoice, invoice_data in invoices_data.items():
            partner = invoice.partner_id.commercial_partner_id.with_company(invoice.company_id)
            if 'eracun' not in invoice_data['sending_methods']:
                continue

            if not partner.eracun_identifier_type or not partner.eracun_identifier_value:
                invoice.eracun_move_state = 'error'
                invoice_data['error'] = _('The partner is missing eRacun Endpoint Type or Value.')
                continue

            if partner._get_eracun_verification_state(invoice_data['invoice_edi_format']) != 'valid':
                invoice.eracun_move_state = 'error'
                invoice_data['error'] = _('Please verify partner configuration in partner settings.')
                continue

            if not self._is_applicable_to_move('eracun', invoice, **invoice_data):
                continue

            if invoice_data.get('ubl_cii_xml_attachment_values'):
                xml_file = invoice_data['ubl_cii_xml_attachment_values']['raw']
                filename = invoice_data['ubl_cii_xml_attachment_values']['name']
            elif invoice.ubl_cii_xml_id and invoice.eracun_move_state not in {'processing', 'done'}:
                xml_file = invoice.ubl_cii_xml_id.raw
                filename = invoice.ubl_cii_xml_id.name
            else:
                invoice.eracun_move_state = 'error'
                builder = invoice.partner_id.commercial_partner_id._get_edi_builder(invoice_data['invoice_edi_format'])
                invoice_data['error'] = _(
                    "Errors occurred while creating the EDI document (format: %s):",
                    builder._description,
                )
                continue

            receiver_identification = f"{partner.eracun_identifier_type}:{partner.eracun_identifier_value}"
            params['documents'].append({
                'filename': filename,
                'receiver': receiver_identification,
                'ubl': b64encode(xml_file).decode(),
            })
            invoices_data_eracun[invoice] = invoice_data

        if not params['documents']:
            return

        edi_user = next(iter(invoices_data)).company_id.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'eracun')

        try:
            response = edi_user._call_eracun_proxy(
                "/api/eracun/1/send_document",
                params=params,
            )
        except AccountEdiProxyError as e:
            for invoice, invoice_data in invoices_data_eracun.items():
                invoice.eracun_move_state = 'error'
                invoice_data['error'] = e.message
        else:
            if response.get('error'):
                # at the moment the only error that can happen here is ParticipantNotReady error
                for invoice, invoice_data in invoices_data_eracun.items():
                    invoice.eracun_move_state = 'error'
                    invoice_data['error'] = response['error']['message']
            else:
                invoices = self.env['account.move']
                for message, (invoice, invoice_data) in zip(response['messages'], invoices_data_eracun.items()):
                    invoice.eracun_message_uuid = message['message_uuid']
                    invoice.eracun_move_state = 'processing'
                    invoices |= invoice
                log_message = _('The document has been sent to the eRacun Access Point for processing')
                invoices._message_log_batch(bodies={invoice.id: log_message for invoice in invoices})
                self.env.ref('l10n_hr_edi.ir_cron_eracun_get_message_status')._trigger(at=fields.Datetime.now() + timedelta(minutes=5))

        if self._can_commit():
            self._cr.commit()
