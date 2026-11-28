import logging

from odoo import models, tools
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.addons.account_peppol.models.account_edi_proxy_user import BATCH_SIZE

_logger = logging.getLogger(__name__)


class AccountEDIProxyUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    def _get_company_details(self):
        return {
            **super()._get_company_details(),
            "peppol_validation_token": self.company_id.peppol_validation_token,
        }

    def _cron_peppol_get_new_tax_data_documents(self):
        edi_users = self.search([
            ('company_id.account_peppol_proxy_state', 'in', ('sender', 'smp_registration', 'receiver')),
            ('company_id.peppol_eas', '=', '0245'),
            ('proxy_type', 'in', self._get_peppol_proxy_types()),
        ])
        edi_users._peppol_get_new_tax_data_documents()

    def _peppol_get_new_tax_data_documents(self):
        need_retrigger = False
        for edi_user in self:
            edi_user = edi_user.with_company(edi_user.company_id)
            try:
                messages = edi_user._call_peppol_proxy(
                    endpoint=edi_user._get_peppol_proxy_endpoint('1/get_tax_data_documents'),
                    params={'limit': self._context.get('peppol_crons_job_count') or BATCH_SIZE},
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
            all_messages = edi_user._call_peppol_proxy(
                endpoint=edi_user._get_peppol_proxy_endpoint('1/get_document'),
                params={'message_uuids': message_uuids},
            )

            processed_uuids = edi_user._peppol_process_new_tax_data_messages(all_messages)

            if not tools.config['test_enable']:
                self.env.cr.commit()
            edi_user._peppol_ack_messages(processed_uuids)

        if need_retrigger:
            self.env.ref('account_peppol.ir_cron_peppol_get_new_tax_data_documents')._trigger()

    def _peppol_process_new_tax_data_messages(self, messages):
        processed_uuids = []
        uuids = {}
        for uuid, message in messages.items():
            if source_uuid := message.get('source_uuid'):
                uuids[source_uuid] = uuid
            else:
                processed_uuids.append(uuid)
        moves_by_uuid = self.env['account.move'].search([
            ('peppol_message_uuid', 'in', list(uuids.keys())),
            ('company_id', '=', self.company_id.id),
        ]).grouped('peppol_message_uuid')
        for source_uuid, uuid_moves in moves_by_uuid.items():
            uuid = uuids[source_uuid]
            content = messages[uuid]
            move = moves_by_uuid[source_uuid][:1]
            attachment = self._create_peppol_attachment(content)
            attachment.write({
                'name': f"{content['document_type']}_{attachment.name}",
                'res_model': 'account.move',
                'res_id': move.id,
            })
            processed_uuids.append(uuid)
            if move.peppol_move_state != 'error':
                error = content.get('error')
                if error and error.get('code') != 702:
                    move._message_log(body=self._peppol_get_message_status_error_body(move, error))
            continue

        return processed_uuids
