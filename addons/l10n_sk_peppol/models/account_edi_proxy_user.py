import logging

from odoo import models, modules, tools
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.addons.account_peppol.models.account_edi_proxy_user import BATCH_SIZE

_logger = logging.getLogger(__name__)


class AccountEDIProxyUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    def _cron_peppol_get_new_tax_data_documents(self):
        edi_users = self.search([
            ('company_id.account_peppol_proxy_state', 'in', ('sender', 'smp_registration', 'receiver')),
            ('company_id.routing_scheme', '=', '0245'),
            ('proxy_type', 'in', self._get_peppol_proxy_types()),
        ])
        edi_users._peppol_get_new_tax_data_documents()

    def _peppol_get_new_tax_data_documents(self):
        need_retrigger = False
        for edi_user in self:
            company = edi_user.company_id
            edi_user = edi_user.with_company(company)

            # Only process moves waiting for a TDD.
            # This prevents looking for TDDs whose associated moves have been deleted and ensures we never acknowledge
            # a TDD before fetching its associated move.
            moves_waiting_for_tdd = self.env['account.move']._get_moves_waiting_for_tdd(company)
            try:
                messages = edi_user._call_peppol_proxy(
                    endpoint=edi_user._get_peppol_proxy_endpoint('1/get_tax_data_documents'),
                    params={
                        'uuids': moves_waiting_for_tdd.mapped('peppol_message_uuid'),
                        'limit': self.env.context.get('peppol_crons_job_count') or BATCH_SIZE,
                    },
                )
            except AccountEdiProxyError as e:
                _logger.error('Error while receiving the document from Peppol Proxy: %s', e.message)
                continue

            has_more = messages.get('has_more', False)
            message_uuids = edi_user._filter_duplicate_messages(messages.get('messages', []))
            if not message_uuids:
                continue

            need_retrigger = need_retrigger or has_more

            # retrieve attachments for filtered messages
            tdd_messages = edi_user._call_peppol_proxy(
                endpoint=edi_user._get_peppol_proxy_endpoint('1/get_document'),
                params={'message_uuids': message_uuids},
            )

            edi_user._peppol_process_new_tax_data_messages(moves_waiting_for_tdd, tdd_messages)

            if not (modules.module.current_test or tools.config['test_enable']):
                self.env.cr.commit()

            edi_user._peppol_ack_messages(list(tdd_messages.keys()))

        if need_retrigger:
            self.env.ref('l10n_sk_peppol.ir_cron_peppol_get_new_tax_data_documents')._trigger()

    def _peppol_process_new_tax_data_messages(self, moves, messages):
        moves_by_uuid = moves.grouped('peppol_message_uuid')
        for content in messages.values():
            source_uuid = content.get('source_uuid')
            move = moves_by_uuid.get(source_uuid)
            if not move:
                continue
            attachment = self._create_peppol_attachment(content)
            attachment.write({
                'name': f"{content['document_type']}_{attachment.name}",
                'res_model': 'account.move',
                'res_id': move.id,
            })
            move.l10n_sk_tdd_attachment_id = attachment.id
            if move.peppol_move_state != 'error':
                error = content.get('error')
                if error and error.get('code') != 702:
                    move._message_log(body=self._peppol_get_message_status_error_body(move, error))
