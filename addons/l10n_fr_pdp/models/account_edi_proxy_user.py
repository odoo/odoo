import logging

from odoo import _, api, fields, models, modules, tools
from odoo.exceptions import UserError

from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.addons.l10n_fr_pdp.tools.demo_utils import handle_demo

_logger = logging.getLogger(__name__)
BATCH_SIZE = 50


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    proxy_type = fields.Selection(selection_add=[('pdp', 'PDP')], ondelete={'pdp': 'cascade'})

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _get_proxy_urls(self):
        urls = super()._get_proxy_urls()
        urls['pdp'] = {
            'prod': 'https://pdp.api.odoo.com',
            # TODO: test url
            # 'test': 'https://pdp.test.odoo.com',
            'test': 'http://localhost:9999',
            'demo': 'demo',
        }
        return urls

    def _get_proxy_identification(self, company, proxy_type):
        if proxy_type != 'pdp':
            return super()._get_proxy_identification(company, proxy_type)
        if not company.pdp_identifier:
            raise UserError(
                _("Please fill the PDP identifier."))
        return f'0225:{company.pdp_identifier}'

    @handle_demo
    def _register_proxy_user(self, company, proxy_type, edi_mode):
        """ Override to avoid using the deprecated route on IAP """
        if proxy_type != 'pdp':
            return super()._register_proxy_user(company, proxy_type, edi_mode)

        private_key_sudo = self.env['certificate.key'].sudo()._generate_rsa_private_key(
            company,
            name=f"{proxy_type}_{edi_mode}_{company.id}.key",
        )
        peppol_identifier = self._get_proxy_identification(company, proxy_type)
        if edi_mode == 'demo':
            # simulate registration
            response = {'id_client': f'demo{company.id}{proxy_type}', 'refresh_token': 'demo'}
        else:
            try:
                # b64encode returns a bytestring, we need it as a string
                response = self._make_request(self._get_server_url(proxy_type, edi_mode) + '/api/pdp/1/connect', params={
                    'dbuuid': company.env['ir.config_parameter'].get_param('database.uuid'),
                    'company_id': company.id,
                    'peppol_identifier': peppol_identifier,
                    'public_key': private_key_sudo._get_public_key_bytes(encoding='pem').decode(),
                })
            except AccountEdiProxyError as e:
                raise UserError(e.message)

        if error_message := response.get('error'):
            raise UserError(error_message)

        return self.create({
            'id_client': response['id_client'],
            'company_id': company.id,
            'proxy_type': 'pdp',
            'edi_mode': edi_mode,
            'edi_identification': peppol_identifier,
            'private_key_id': private_key_sudo.id,
            'refresh_token': response['refresh_token'],
        })

    @handle_demo
    def _call_pdp_proxy(self, endpoint, params=None):
        self.ensure_one()
        if self.proxy_type != 'pdp':
            raise UserError(_('EDI user should be of type PDP'))

        params = params or {}
        try:
            response = self._make_request(
                f"{self._get_server_url()}{endpoint}",
                params=params,
            )
        except AccountEdiProxyError as e:
            if e.code == 'no_such_user_found':
                # TODO: may be too "aggressive" in production; but useful for testing?
                self.company_id.l10n_fr_pdp_proxy_state = False
                self.unlink()
                if not modules.module.current_test:
                    self.env.cr.commit()
                raise UserError(_('We could not find a user with this information on our server. Please check your information.'))
            raise UserError(e.message)

        if 'error' in response:
            errors = [
                response['error'].get('subject'),
                response['error'].get('message'),
            ]
            message = '\n'.join([error for error in errors if error])
            raise UserError(message or _('Connection error, please try again later.'))
        return response

    def _get_pdp_company_details(self):
        self.ensure_one()
        return {
            'peppol_company_name': self.company_id.display_name,
            'peppol_company_vat': self.company_id.vat,
            'peppol_company_street': self.company_id.street,
            'peppol_company_city': self.company_id.city,
            'peppol_company_zip': self.company_id.zip,
            'peppol_country_code': self.company_id.country_id.code,
            'peppol_phone_number': self.company_id.pdp_phone_number,
            'peppol_contact_email': self.company_id.pdp_contact_email,
            'peppol_webhook_endpoint': self.company_id._get_pdp_webhook_endpoint(),
            'peppol_webhook_token': self._generate_pdp_webhook_token(),
        }

    def _pdp_register_receiver(self):
        # remove in master
        self.ensure_one()
        company = self.company_id
        if company.l10n_fr_pdp_proxy_state in ('pending', 'receiver'):
            # a participant can only try registering as a receiver if they are not registered
            pdp_state_translated = dict(company._fields['l10n_fr_pdp_proxy_state'].selection)[company.l10n_fr_pdp_proxy_state]
            raise UserError(_('Cannot register a user with a %s application', pdp_state_translated))

        params = {
            'company_details': self._get_pdp_company_details(),
            'supported_identifiers': list(self.company_id._pdp_supported_document_types()),
        }
        self._call_pdp_proxy(
            endpoint='/api/pdp/1/register_receiver',
            params=params,
        )
        company.l10n_fr_pdp_proxy_state = 'pending'

        datetime_in_1_hour = fields.Datetime.add(fields.Datetime.now(), hours=1)
        self.env.ref('l10n_fr_pdp.ir_cron_pdp_get_participant_status')._trigger(at=datetime_in_1_hour)

    def _pdp_deregister_participant(self):
        self.ensure_one()

        proxy_state = self.company_id.l10n_fr_pdp_proxy_state
        if proxy_state == 'receiver':
            # fetch all documents and message statuses before unlinking the edi user
            # so that the invoices are acknowledged
            self._cron_pdp_get_message_status()
            self._cron_pdp_get_new_documents()
            if not tools.config['test_enable'] and not modules.module.current_test:
                self.env.cr.commit()

        if proxy_state:
            self._call_pdp_proxy(endpoint='/api/pdp/1/cancel_pdp_registration')

        self.company_id.l10n_fr_pdp_proxy_state = False
        self.unlink()

    def _pdp_get_participant_status(self):
        for edi_user in self:
            edi_user = edi_user.with_company(edi_user.company_id)
            try:
                proxy_user = edi_user._call_pdp_proxy("/api/pdp/1/participant_status")
            except AccountEdiProxyError as e:
                _logger.error('Error while updating PDP participant status: %s', e)
                continue

            if proxy_user['pdp_state'] in ('pending', 'receiver', 'rejected'):
                edi_user.company_id.l10n_fr_pdp_proxy_state = proxy_user['pdp_state']

    def _generate_pdp_webhook_token(self):
        self.ensure_one()
        expiration = 30 * 24  # in 30 days
        msg = [self.id, self.company_id._get_pdp_webhook_endpoint()]
        payload = tools.hash_sign(self.sudo().env, 'account_pdp_webhook', msg, expiration_hours=expiration)
        return payload

    @api.model
    def _get_pdp_user_from_token(self, token: str, url: str):
        try:
            if not (payload := tools.verify_hash_signed(self.sudo().env, 'account_pdp_webhook', token)):
                return None
        except ValueError:
            return None
        else:
            user_id, endpoint = payload
            if not url.startswith(endpoint):
                return None
            return self.browse(user_id).exists()

    def _pdp_reset_webhook(self):
        for edi_user in self:
            edi_user._call_pdp_proxy(
                '/api/pdp/1/set_webhook',
                params={
                    'webhook_url': edi_user.company_id._get_pdp_webhook_endpoint(),
                    'token': edi_user._generate_pdp_webhook_token()
                }
            )

    def _pdp_import_invoice(self, attachment, partner_endpoint, pdp_state, uuid):
        """Save new documents in an accounting journal, when one is specified on the company.

        :param attachment: the new document
        :param partner_endpoint: DEPRECATED - to be removed in master
        :param pdp_state: the state of the received PDP document
        :param uuid: the UUID of the PDP document
        :return: `True` if the document was saved, `False` if it was not
        """
        self.ensure_one()
        journal = self.company_id.pdp_purchase_journal_id
        if not journal:
            return False

        move = self.env['account.move'].create({
            'journal_id': journal.id,
            'move_type': 'in_invoice',
            'pdp_move_state': pdp_state,
            'pdp_message_uuid': uuid,
        })
        if 'is_in_extractable_state' in move._fields:
            move.is_in_extractable_state = False

        move._extend_with_attachments(attachment, new=True)
        move._message_log(
            body=_(
                "PDP document (UUID: %(uuid)s) has been received successfully",
                uuid=uuid,
            ),
            attachment_ids=attachment.ids,
        )
        move._autopost_bill()
        attachment.write({'res_model': 'account.move', 'res_id': move.id})
        return True

    def _pdp_get_new_documents(self, batch_size=None):
        job_count = batch_size or BATCH_SIZE
        need_retrigger = False
        params = {
            'domain': {
                'direction': 'incoming',
                'errors': False,
            }
        }
        for edi_user in self:
            edi_user = edi_user.with_company(edi_user.company_id)
            params['domain']['receiver_identifier'] = edi_user.edi_identification
            try:
                # request all messages that haven't been acknowledged
                messages = edi_user._call_pdp_proxy(
                    "/api/pdp/1/get_all_documents",
                    params=params,
                )
            except UserError as e:
                _logger.error('Error while receiving the document from PDP Proxy: %s', e)
                continue

            message_uuids = [
                message['uuid']
                for message in messages.get('messages', [])
            ]
            if not message_uuids:
                continue

            need_retrigger = need_retrigger or len(message_uuids) > job_count
            message_uuids = message_uuids[:job_count]

            proxy_acks = []
            # retrieve attachments for filtered messages
            all_messages = edi_user._call_pdp_proxy(
                "/api/pdp/1/get_document",
                params={'message_uuids': message_uuids},
            )

            for uuid, content in all_messages.items():
                enc_key = content["enc_key"]
                document_content = content["document"]
                filename = content["filename"] or 'attachment'  # default to attachment, which should not usually happen
                decoded_document = edi_user._decrypt_data(document_content, enc_key)
                attachment = self.env["ir.attachment"].create(
                    {
                        "name": f"{filename}.xml",
                        "raw": decoded_document,
                        "type": "binary",
                        "mimetype": "application/xml",
                    }
                )
                if edi_user._pdp_import_invoice(attachment, None, content["state"], uuid):
                    # Only acknowledge when we saved the document somewhere
                    proxy_acks.append(uuid)

            if not tools.config['test_enable']:
                self.env.cr.commit()
            if proxy_acks:
                edi_user._call_pdp_proxy(
                    "/api/pdp/1/ack",
                    params={'message_uuids': proxy_acks},
                )
        if need_retrigger:
            self.env.ref('l10n_fr_pdp.ir_cron_pdp_get_new_documents')._trigger()

    def _pdp_get_message_status(self, batch_size=None):
        job_count = batch_size or BATCH_SIZE
        need_retrigger = False
        for edi_user in self:
            edi_user_moves = self.env['account.move'].search(
                [
                    ('pdp_move_state', '=', 'processing'),
                    ('company_id', '=', edi_user.company_id.id),
                ],
                limit=job_count + 1,
            )
            if not edi_user_moves:
                continue

            need_retrigger = need_retrigger or len(edi_user_moves) > job_count
            message_uuids = {move.pdp_message_uuid: move for move in edi_user_moves[:job_count]}
            messages_to_process = edi_user._call_pdp_proxy(
                "/api/pdp/1/get_document",
                params={'message_uuids': list(message_uuids.keys())},
            )

            for uuid, content in messages_to_process.items():
                if uuid == 'error':
                    # this rare edge case can happen if the participant is not active on the proxy side
                    # in this case we can't get information about the invoices
                    edi_user_moves.pdp_move_state = 'error'
                    log_message = _("PDP error: %s", content['message'])
                    edi_user_moves._message_log_batch(bodies={move.id: log_message for move in edi_user_moves})
                    break

                move = message_uuids[uuid]
                if content.get('error'):
                    # "PDP request not ready" error:
                    # thrown when the IAP is still processing the message
                    if content['error'].get('code') == 702:
                        continue

                    move.pdp_move_state = 'error'
                    move._message_log(body=_("PDP error: %s", content['error'].get('data', {}).get('message') or content['error']['message']))
                    continue

                move.pdp_move_state = content['state']
                move._message_log(body=_('PDP status update: %s', content['state']))

            edi_user._call_pdp_proxy(
                "/api/pdp/1/ack",
                params={'message_uuids': list(message_uuids.keys())},
            )
        if need_retrigger:
            self.env.ref('l10n_fr_pdp.ir_cron_pdp_get_message_status')._trigger()

    # -------------------------------------------------------------------------
    # CRONS
    # -------------------------------------------------------------------------

    def _cron_pdp_get_new_documents(self):
        edi_users = self.search([('proxy_type', '=', 'pdp'), ('company_id.l10n_fr_pdp_proxy_state', '=', 'receiver')])
        edi_users._pdp_get_new_documents()

    def _cron_pdp_get_message_status(self):
        edi_users = self.search([('proxy_type', '=', 'pdp'), ('company_id.l10n_fr_pdp_proxy_state', '=', 'receiver')])
        edi_users._pdp_get_message_status()

    def _cron_pdp_get_participant_status(self):
        edi_users = self.search([('proxy_type', '=', 'pdp')])
        edi_users._pdp_get_participant_status()

        # throughout the registration process, we need to check the status more frequently
        if self.search_count([('company_id.l10n_fr_pdp_proxy_state', '=', 'pending')], limit=1):
            datetime_in_1_hour = fields.Datetime.add(fields.Datetime.now(), hours=1)
            self.env.ref('l10n_fr_pdp.ir_cron_pdp_get_participant_status')._trigger(at=datetime_in_1_hour)

    def _cron_pdp_webhook_keepalive(self):
        edi_users = self.search([('proxy_type', '=', 'pdp'), ('company_id.l10n_fr_pdp_proxy_state', '=', 'receiver')])
        edi_users._pdp_reset_webhook()
