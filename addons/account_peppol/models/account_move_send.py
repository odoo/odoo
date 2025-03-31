from base64 import b64encode
from datetime import timedelta

from odoo import fields, models, _
from odoo.addons.account.models.company import PEPPOL_LIST
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError

class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        def peppol_partner(moves):
            return moves.partner_id.commercial_partner_id

        def filter_peppol_state(moves, states):
            return peppol_partner(moves.filtered(
                lambda m: self.env['res.partner']._get_peppol_verification_state(
                    peppol_partner(m).peppol_endpoint,
                    peppol_partner(m).peppol_eas,
                    moves_data[m]['invoice_edi_format']) in states))

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
        can_send = self.env['account_edi_proxy_client.user']._get_can_send_domain()
        any_moves_not_sent_peppol = any(move.peppol_move_state not in ('processing', 'done') for move in moves)
        always_on_companies = moves.company_id.filtered(
            lambda c: c.country_code in info_always_on_countries and c.account_peppol_proxy_state not in can_send
        )
        if always_on_companies and any_moves_not_sent_peppol and not filter_peppol_state(moves, ['not_valid', 'not_verified']):
            alerts.pop('account_edi_ubl_cii_configure_company', False)
            alerts['account_peppol_what_is_peppol'] = {
                'message': _("You can send this invoice electronically via Peppol."),
                **what_is_peppol_alert,
            }
        elif (peppol_not_selected_partners := filter_peppol_state(not_peppol_moves, ['valid'])) and any_moves_not_sent_peppol:
            # Check for not peppol partners that are on the network.
            if len(peppol_not_selected_partners) == 1:
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

    def _get_mail_layout(self):
        # EXTENDS 'account'
        # TODO remove the fallback in master
        if self.env.ref('account_peppol.mail_notification_layout_with_responsible_signature_and_peppol',
                        raise_if_not_found=False):
            return 'account_peppol.mail_notification_layout_with_responsible_signature_and_peppol'
        return super()._get_mail_layout()

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
            partner = move.partner_id.commercial_partner_id.with_company(move.company_id)
            invoice_edi_format = partner._get_peppol_edi_format()
            return all([
                self._is_applicable_to_company(method, move.company_id),
                self.env['res.partner']._get_peppol_verification_state(partner.peppol_endpoint, partner.peppol_eas, invoice_edi_format) == 'valid',
                move.company_id.account_peppol_proxy_state != 'rejected',
                move._need_ubl_cii_xml(invoice_edi_format)
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

                if self.env['res.partner']._get_peppol_verification_state(partner.peppol_endpoint, partner.peppol_eas, invoice_data['invoice_edi_format']) != 'valid':
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
            response = edi_user._call_peppol_proxy(
                "/api/peppol/1/send_document",
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
                for message, (invoice, invoice_data) in zip(response['messages'], invoices_data_peppol.items()):
                    invoice.peppol_message_uuid = message['message_uuid']
                    invoice.peppol_move_state = 'processing'
                    invoices |= invoice
                log_message = _('The document has been sent to the Peppol Access Point for processing')
                invoices._message_log_batch(bodies={invoice.id: log_message for invoice in invoices})
                self.env.ref('account_peppol.ir_cron_peppol_get_message_status')._trigger(at=fields.Datetime.now() + timedelta(minutes=5))

        if self._can_commit():
            self._cr.commit()

    def action_what_is_peppol_activate(self, moves):
        companies = moves.company_id
        can_send = self.env['account_edi_proxy_client.user']._get_can_send_domain()
        if len(companies) == 1 and companies.account_peppol_proxy_state not in can_send:
            action = self.env['peppol.registration']._action_open_peppol_form()
            action['context'].update({
                'active_model': 'account.move',
                'active_ids': moves.ids,
                'dialog_size': 'medium',
            })
            return action
        else:
            return moves.action_send_and_print()
