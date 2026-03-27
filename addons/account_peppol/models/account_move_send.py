import logging

from base64 import b64encode
from datetime import timedelta

from odoo import api, fields, models, _

from odoo.addons.account.models.company import PEPPOL_LIST
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.addons.account_peppol.exceptions import get_peppol_error_message

_logger = logging.getLogger(__name__)


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _get_default_sending_methods(self, move) -> set:
        """ By default, we use the sending method set on the partner or email and peppol. """
        # EXTENDS 'account'
        default_sending_methods = super()._get_default_sending_methods(move)
        if self._is_applicable_to_move('peppol', move):
            default_sending_methods.add('peppol')
        return default_sending_methods

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        def peppol_partner(moves):
            return moves.partner_id.commercial_partner_id

        def filter_peppol_state(moves, states):
            return peppol_partner(
                moves.filtered(lambda m: peppol_partner(m).peppol_verification_state in states)
            )

        alerts = super()._get_alerts(moves, moves_data)
        # Check for invalid peppol partners.
        peppol_moves = moves.filtered(lambda m: 'peppol' in moves_data[m]['sending_methods'])
        invalid_partners = filter_peppol_state(peppol_moves, ['not_valid_format'])
        if invalid_partners and not 'account_edi_ubl_cii_configure_partner' in alerts:
            alerts['account_peppol_warning_partner'] = {
                'message': _("Customer is on Peppol but did not enable receiving documents."),
                'action_text': _("View Partner(s)"),
                'action': invalid_partners._get_records_action(name=_("Check Partner(s)")),
            }
        not_peppol_moves = moves.filtered(lambda m: 'peppol' not in moves_data[m]['sending_methods'])
        what_is_peppol_alert = {
            'level': 'info',
            'action_text': _("Why should you use it ?"),
            'action': {
                'name': _("Why should I use PEPPOL ?"),
                'type': 'ir.actions.client',
                'tag': 'account_peppol.what_is_peppol',
                'target': 'new',
                'context': {
                    'footer': False,
                    'dialog_size': 'medium',
                    'action_on_activate': self.action_what_is_peppol_activate(moves),
                },
            },
        }
        info_always_on_countries = {'BE', 'FI', 'LU', 'LV', 'NL', 'NO', 'SE'}
        any_moves_not_sent_peppol = any(move.peppol_move_state not in ('processing', 'done') for move in moves)
        always_on_companies = moves.company_id.filtered(
            lambda c: c.country_code in info_always_on_countries and not c.peppol_can_send
        )
        if all((
            always_on_companies,
            any_moves_not_sent_peppol,
            not filter_peppol_state(moves, ['not_valid', 'not_verified']),
        )):
            alerts.pop('account_edi_ubl_cii_configure_company', False)
            alerts['account_peppol_what_is_peppol'] = {
                'message': _("You can send this invoice electronically via Peppol."),
                **what_is_peppol_alert,
            }
        elif all((
            (peppol_not_selected_partners := filter_peppol_state(not_peppol_moves, ['valid'])),
            any_moves_not_sent_peppol,
            len(peppol_not_selected_partners) == 1,  # Check for not peppol partners that are on the network
        )):
            alerts['account_peppol_partner_want_peppol'] = {
                'message': _(
                    "%s has requested electronic invoices reception on Peppol.",
                    peppol_not_selected_partners.display_name
                ),
                **what_is_peppol_alert,
            }
        return alerts

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    def _get_default_invoice_edi_format(self, move, **kwargs) -> str:
        # EXTENDS 'account' - default on bis3 if Peppol is set but no format on the partner
        invoice_edi_format = super()._get_default_invoice_edi_format(move, **kwargs)
        if 'peppol' in kwargs.get('sending_methods', []):
            return move.partner_id.with_company(move.company_id)._get_peppol_edi_format()
        return invoice_edi_format

    def _get_mail_layout(self):
        # OVERRIDE 'account'
        return 'account_peppol.mail_notification_layout_with_responsible_signature_and_peppol'

    def _do_peppol_pre_send(self, moves):
        if len(moves.company_id) == 1:
            if not moves.company_id.peppol_can_send:
                return self.env['peppol.registration'].with_context(default_company_id=moves.company_id.id)._action_open_peppol_form(reopen=False)

        for move in moves:
            if move.peppol_move_state in ('ready', False):
                move.peppol_move_state = 'to_send'

    def _is_applicable_to_company(self, method, company):
        # EXTENDS 'account'
        if method == 'peppol':
            return company.country_code in PEPPOL_LIST and company.account_peppol_proxy_state != 'rejected'
        else:
            return super()._is_applicable_to_company(method, company)

    def _is_applicable_to_move(self, method, move, **move_data):
        # EXTENDS 'account'
        if method == 'peppol':
            partner = move.partner_id.commercial_partner_id.with_company(move.company_id)
            invoice_edi_format = move_data.get('invoice_edi_format') or partner._get_peppol_edi_format()
            if partner.peppol_verification_state == 'not_verified':
                partner.button_account_peppol_check_partner_endpoint(company=move.company_id)
            return all([
                partner.country_code in PEPPOL_LIST,
                self._is_applicable_to_company(method, move.company_id),
                partner.peppol_verification_state == 'valid',
                move.company_id.account_peppol_proxy_state != 'rejected',
                move._need_ubl_cii_xml(invoice_edi_format)
                or move.ubl_cii_xml_id and move.peppol_move_state not in ('processing', 'done'),
            ])
        else:
            return super()._is_applicable_to_move(method, move, **move_data)

    def _hook_if_errors(self, moves_data, allow_raising=True):
        # EXTENDS 'account'
        # to update `peppol_move_state` as `error` to show users that something went wrong
        # because those moves that failed XML/PDF files generation are not sent via Peppol
        moves_failed_file_generation = self.env['account.move']
        for move, move_data in moves_data.items():
            if 'peppol' in move_data['sending_methods'] and move_data.get('blocking_error'):
                moves_failed_file_generation |= move

        moves_failed_file_generation.peppol_move_state = 'error'

        return super()._hook_if_errors(moves_data, allow_raising=allow_raising)

    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)

        params = {'documents': []}
        invoices_data_peppol = {}
        to_lock_peppol_invoices = self.env['account.move']
        for invoice, invoice_data in invoices_data.items():
            partner = invoice.partner_id.commercial_partner_id.with_company(invoice.company_id)
            if 'peppol' in invoice_data['sending_methods'] and self._is_applicable_to_move('peppol', invoice, **invoice_data):

                if invoice_data.get('ubl_cii_xml_attachment_values'):
                    xml_file = invoice_data['ubl_cii_xml_attachment_values']['raw']
                    filename = invoice_data['ubl_cii_xml_attachment_values']['name']
                elif invoice.ubl_cii_xml_id and invoice.peppol_move_state not in ('processing', 'done'):
                    xml_file = invoice.ubl_cii_xml_id.raw
                    filename = invoice.ubl_cii_xml_id.name
                else:
                    invoice.peppol_move_state = 'error'
                    builder = invoice.partner_id.commercial_partner_id._get_edi_builder(invoice_data['invoice_edi_format'])
                    invoice_data['error'] = _(
                        "Errors occurred while creating the EDI document (format: %s):",
                        builder._description
                    )
                    continue

                if invoice.invoice_pdf_report_id and self._needs_ubl_postprocessing(invoice_data):
                    self._postprocess_invoice_ubl_xml(invoice, invoice_data)
                    xml_file = invoice_data['ubl_cii_xml_attachment_values']['raw']
                    filename = invoice_data['ubl_cii_xml_attachment_values']['name']

                if len(xml_file) > 64000000:
                    invoice_data['error'] = _("Invoice %s is too big to send via peppol (64MB limit)", invoice.name)
                    continue

                receiver_identification = f"{partner.peppol_eas}:{partner.peppol_endpoint}"
                params['documents'].append({
                    'filename': filename,
                    'receiver': receiver_identification,
                    'ubl': b64encode(xml_file).decode(),
                })
                invoices_data_peppol[invoice] = invoice_data
                to_lock_peppol_invoices |= invoice

        if not params['documents']:
            return

        edi_user = next(iter(invoices_data)).company_id.account_peppol_edi_user

        if not self.env['res.company']._with_locked_records(to_lock_peppol_invoices, allow_raising=False):
            _logger.error('Failed to lock invoices for Peppol sending')
            return

        try:
            response = edi_user._call_peppol_proxy(
                "/api/peppol/1/send_document",
                params=params,
            )
        except AccountEdiProxyError as e:
            for invoice, invoice_data in invoices_data_peppol.items():
                invoice.peppol_move_state = 'error'
                invoice_data['error'] = {'error_title': e.message}
        else:
            if error_vals := response.get('error'):
                # at the moment the only error that can happen here is ParticipantNotReady error
                for invoice, invoice_data in invoices_data_peppol.items():
                    invoice.peppol_move_state = 'error'
                    invoice_data['error'] = {
                        'error_title': get_peppol_error_message(self.env, error_vals),
                    }
            else:
                # the response only contains message uuids,
                # so we have to rely on the order to connect peppol messages to account.move
                attachments_linked_message = _("The invoice has been sent to the Peppol Access Point. The following attachments were sent with the XML:")
                attachments_not_linked_message = _("Some attachments could not be sent with the XML:")
                for message, (invoice, invoice_data) in zip(response['messages'], invoices_data_peppol.items()):
                    invoice.peppol_message_uuid = message['message_uuid']
                    invoice.peppol_move_state = 'processing'
                    attachments_linked, attachments_not_linked = self._get_ubl_available_attachments(
                        invoice_data.get('mail_attachments_widget', []),
                        invoice_data['invoice_edi_format']
                    )
                    if attachments_not_linked:
                        invoice._message_log(body=attachments_not_linked_message, attachment_ids=attachments_not_linked.mapped('id'))

                    base_attachments = [
                        (invoice_data[key]['name'], invoice_data[key]['raw'])
                        for key in ['pdf_attachment_values', 'ubl_cii_xml_attachment_values']
                        if invoice_data.get(key)
                    ]

                    attachments_embedded = [
                        (attachment.name, attachment.raw)
                        for attachment in attachments_linked
                    ] + base_attachments

                    new_message = invoice.message_post(
                        body=attachments_linked_message,
                        attachments=attachments_embedded
                    )

                    if new_message.attachment_ids.ids:
                        if invoice.message_main_attachment_id in new_message.attachment_ids:
                            invoice.message_main_attachment_id = None
                        self.env.cr.execute("UPDATE ir_attachment SET res_id = NULL WHERE id IN %s", [tuple(new_message.attachment_ids.ids)])
                        new_message.attachment_ids.invalidate_recordset(['res_id', 'res_model'], flush=False)
                        new_message.attachment_ids.write({
                            'res_model': new_message._name,
                            'res_id': new_message.id,
                        })
                self.env.ref('account_peppol.ir_cron_peppol_get_message_status')._trigger(at=fields.Datetime.now() + timedelta(minutes=5))

        if self._can_commit():
            self.env.cr.commit()

    def action_what_is_peppol_activate(self, moves):
        companies = moves.company_id
        if len(companies) == 1 and not companies.peppol_can_send:
            action = self.env['peppol.registration']._action_open_peppol_form()
            action['context'] = {
                'active_model': "account.move",
                'active_ids': moves.ids,
                'dialog_size': 'medium',
                **action['context'],
            }
            return action
        else:
            # go back to previous (send and print) action
            # to avoid doing participant SML lookup again, we don't go through action_send_and_print
            return {
                'name': _("Send"),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'account.move.send.wizard' if len(moves) == 1 else 'account.move.send.batch.wizard',
                'target': 'new',
                'context': {
                    'active_model': 'account.move',
                    'active_ids': moves.ids
                },
            }
