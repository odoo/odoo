# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models, modules, tools
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.addons.account_peppol.tools.demo_utils import handle_demo
from odoo.exceptions import UserError
from odoo.tools import split_every

_logger = logging.getLogger(__name__)
BATCH_SIZE = 50


class Account_Edi_Proxy_ClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    proxy_type = fields.Selection(selection_add=[('peppol', 'PEPPOL')], ondelete={'peppol': 'cascade'})

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    @handle_demo
    def _make_request(self, url, params=False):
        # extends account_edi_proxy_client to update peppol_proxy_state
        # of archived users
        try:
            result = super()._make_request(url, params)
        except AccountEdiProxyError as e:
            if (
                e.code == 'no_such_user'
                and not self.active
                and not self.company_id.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'peppol')
            ):
                self.company_id.write({
                    'account_peppol_proxy_state': 'not_registered',
                    'account_peppol_migration_key': False,
                })
                # commit the above changes before raising below
                if not modules.module.current_test:
                    self.env.cr.commit()
            raise AccountEdiProxyError(e.code, e.message)
        return result

    def _get_proxy_urls(self):
        urls = super()._get_proxy_urls()
        urls['peppol'] = {
            'prod': 'https://peppol.api.odoo.com',
            'test': 'https://peppol.test.odoo.com',
            'demo': 'demo',
        }
        return urls

    def _call_peppol_proxy(self, endpoint, params=None):
        self.ensure_one()

        params = params or {}
        try:
            response = self._make_request(
                f"{self._get_server_url()}{endpoint}",
                params=params,
            )
        except AccountEdiProxyError as e:
            raise UserError(e.message)

        if 'error' in response:
            error_message = response['error'].get('message') or response['error'].get('data', {}).get('message')
            raise UserError(error_message or _('Connection error, please try again later.'))
        return response

    @api.model
    def _get_can_send_domain(self):
        return ('sender', 'smp_registration', 'receiver')

    def _check_company_on_peppol(self, company, edi_identification):
        if (
            not company.account_peppol_migration_key
            and (participant_info := company.partner_id._get_participant_info(edi_identification)) is not None
            and company.partner_id._check_peppol_participant_exists(participant_info, edi_identification, check_company=True)
        ):
            error_msg = _(
                "A participant with these details has already been registered on the network. "
                "If you have previously registered to an alternative Peppol service, please deregister from that service, "
                "or request a migration key before trying again. "
            )

            if isinstance(participant_info, str):
                error_msg += _("The Peppol service that is used is likely to be %s.", participant_info)
            raise UserError(error_msg)

    # -------------------------------------------------------------------------
    # CRONS
    # -------------------------------------------------------------------------

    def _cron_peppol_get_new_documents(self):
        edi_users = self.search([('company_id.account_peppol_proxy_state', '=', 'receiver')])
        edi_users._peppol_get_new_documents()

    def _cron_peppol_get_message_status(self):
        edi_users = self.search([('company_id.account_peppol_proxy_state', 'in', self._get_can_send_domain())])
        edi_users._peppol_get_message_status()

    def _cron_peppol_get_participant_status(self):
        edi_users = self.search([('company_id.account_peppol_proxy_state', 'in', ['in_verification', 'sender', 'smp_registration'])])
        edi_users._peppol_get_participant_status()

    @api.model
    def _cron_notify_incoming_peppol_invoices(self):
        for user in self.search([
            ('proxy_type', '=', 'peppol'),
        ]):
            incoming_peppol_invoices = self.env['account.move'].search([
                ('company_id.account_edi_proxy_client_ids', '=', user.id),
                ('peppol_notify_pending', '=', True),
                ('move_type', '=', 'in_invoice'),
            ])
            if not incoming_peppol_invoices:
                continue

            incoming_peppol_invoices_count = len(incoming_peppol_invoices)

            self.env.ref('account_peppol.mail_notification_peppol_incoming_invoices').with_context(
                invoice_count=incoming_peppol_invoices_count,
            ).send_mail(user.id)

            incoming_peppol_invoices['peppol_notify_pending'] = False
            self.env.cr.commit()

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def _get_proxy_identification(self, company, proxy_type):
        if proxy_type == 'peppol':
            if not company.peppol_eas or not company.peppol_endpoint:
                raise UserError(
                    _("Please fill in the EAS code and the Participant ID code."))
            return f'{company.peppol_eas}:{company.peppol_endpoint}'
        return super()._get_proxy_identification(company, proxy_type)

    def _peppol_import_invoice(self, attachment, partner_endpoint, peppol_state, uuid):
        """Save new documents in an accounting journal, when one is specified on the company.

        :param attachment: the new document
        :param partner_endpoint: a string containing the sender's Peppol endpoint
        :param peppol_state: the state of the received Peppol document
        :param uuid: the UUID of the Peppol document
        :return: `True` if the document was saved, `False` if it was not
        """
        self.ensure_one()
        journal = self.company_id.peppol_purchase_journal_id
        if not journal:
            return False

        move = self.env['account.move'].create({
            'journal_id': journal.id,
            'move_type': 'in_invoice',
            'peppol_move_state': peppol_state,
            'peppol_message_uuid': uuid,
            'peppol_notify_pending': True,
        })
        if 'is_in_extractable_state' in move._fields:
            move.is_in_extractable_state = False

        move._extend_with_attachments(attachment, new=True)
        move._message_log(
            body=_(
                "Peppol document (UUID: %(uuid)s) has been received successfully.\n(Sender endpoint: %(endpoint)s)",
                uuid=uuid,
                endpoint=partner_endpoint,
            ),
            attachment_ids=attachment.ids,
        )

        attachment.write({'res_model': 'account.move', 'res_id': move.id})
        return True

    def _peppol_get_new_documents(self):
        params = {
            'domain': {
                'direction': 'incoming',
                'errors': False,
            }
        }
        for edi_user in self:
            params['domain']['receiver_identifier'] = edi_user.edi_identification
            try:
                # request all messages that haven't been acknowledged
                messages = edi_user._make_request(
                    url=f"{edi_user._get_server_url()}/api/peppol/1/get_all_documents",
                    params=params,
                )
            except AccountEdiProxyError as e:
                _logger.error(
                    'Error while receiving the document from Peppol Proxy: %s', e.message)
                continue

            message_uuids = [
                message['uuid']
                for message in messages.get('messages', [])
            ]
            if not message_uuids:
                continue

            for uuids in split_every(BATCH_SIZE, message_uuids):
                proxy_acks = []
                # retrieve attachments for filtered messages
                all_messages = edi_user._make_request(
                    f"{edi_user._get_server_url()}/api/peppol/1/get_document",
                    {'message_uuids': uuids},
                )

                for uuid, content in all_messages.items():
                    enc_key = content["enc_key"]
                    document_content = content["document"]
                    filename = content["filename"] or 'attachment'  # default to attachment, which should not usually happen
                    partner_endpoint = content["accounting_supplier_party"]
                    decoded_document = edi_user._decrypt_data(document_content, enc_key)
                    attachment = self.env["ir.attachment"].create(
                        {
                            "name": f"{filename}.xml",
                            "raw": decoded_document,
                            "type": "binary",
                            "mimetype": "application/xml",
                        }
                    )
                    if edi_user._peppol_import_invoice(attachment, partner_endpoint, content["state"], uuid):
                        # Only acknowledge when we saved the document somewhere
                        proxy_acks.append(uuid)

                if not tools.config['test_enable']:
                    self.env.cr.commit()
                if proxy_acks:
                    edi_user._make_request(
                        f"{edi_user._get_server_url()}/api/peppol/1/ack",
                        {'message_uuids': proxy_acks},
                    )

    def _peppol_get_message_status(self):
        for edi_user in self:
            edi_user_moves = self.env['account.move'].search([
                ('peppol_move_state', '=', 'processing'),
                ('company_id', '=', edi_user.company_id.id),
            ])
            if not edi_user_moves:
                continue

            message_uuids = {move.peppol_message_uuid: move for move in edi_user_moves}
            for uuids in split_every(BATCH_SIZE, message_uuids.keys()):
                messages_to_process = edi_user._make_request(
                    f"{edi_user._get_server_url()}/api/peppol/1/get_document",
                    {'message_uuids': uuids},
                )

                for uuid, content in messages_to_process.items():
                    if uuid == 'error':
                        # this rare edge case can happen if the participant is not active on the proxy side
                        # in this case we can't get information about the invoices
                        edi_user_moves.peppol_move_state = 'error'
                        log_message = _("Peppol error: %s", content['message'])
                        edi_user_moves._message_log_batch(bodies={move.id: log_message for move in edi_user_moves})
                        break

                    move = message_uuids[uuid]
                    if content.get('error'):
                        # "Peppol request not ready" error:
                        # thrown when the IAP is still processing the message
                        if content['error'].get('code') == 702:
                            continue

                        move.peppol_move_state = 'error'
                        move._message_log(body=_("Peppol error: %s", content['error']['message']))
                        continue

                    move.peppol_move_state = content['state']
                    move._message_log(body=_('Peppol status update: %s', content['state']))

                edi_user._make_request(
                    f"{edi_user._get_server_url()}/api/peppol/1/ack",
                    {'message_uuids': uuids},
                )

    def _peppol_get_participant_status(self):
        for edi_user in self:
            try:
                proxy_user = edi_user._make_request(
                    f"{edi_user._get_server_url()}/api/peppol/2/participant_status")
            except AccountEdiProxyError as e:
                _logger.error('Error while updating Peppol participant status: %s', e)
                continue

            if proxy_user['peppol_state'] in ('sender', 'smp_registration', 'receiver', 'rejected'):
                edi_user.company_id.account_peppol_proxy_state = proxy_user['peppol_state']

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    @handle_demo
    def _register_proxy_user(self, company, proxy_type, edi_mode):
        # EXTENDS 'account_edi_ubl_cii' - add handle_demo
        return super()._register_proxy_user(company, proxy_type, edi_mode)

    def _peppol_migrate_registration(self):
        """Migrates AWAY from Odoo's SMP."""
        self.ensure_one()
        response = self._call_peppol_proxy(endpoint='/api/peppol/1/migrate_peppol_registration')
        if migration_key := response.get('migration_key'):
            self.company_id.account_peppol_migration_key = migration_key

    def _get_company_details(self):
        self.ensure_one()
        return {
            'peppol_company_name': self.company_id.display_name,
            'peppol_company_vat': self.company_id.vat,
            'peppol_company_street': self.company_id.street,
            'peppol_company_city': self.company_id.city,
            'peppol_company_zip': self.company_id.zip,
            'peppol_country_code': self.company_id.country_id.code,
            'peppol_phone_number': self.company_id.account_peppol_phone_number,
            'peppol_contact_email': self.company_id.account_peppol_contact_email,
            'peppol_migration_key': self.company_id.account_peppol_migration_key,
        }

    def _peppol_register_sender(self):
        self.ensure_one()
        params = {
            'company_details': self._get_company_details(),
        }
        self._call_peppol_proxy(
            endpoint='/api/peppol/1/register_sender',
            params=params,
        )
        self.company_id.account_peppol_proxy_state = 'sender'

    def _peppol_register_receiver(self):
        self.ensure_one()
        params = {
            'company_details': self._get_company_details(),
            'supported_identifiers': list(self.company_id._peppol_supported_document_types())
        }
        self._call_peppol_proxy(
            endpoint='/api/peppol/1/register_receiver',
            params=params,
        )
        self.company_id.account_peppol_proxy_state = 'smp_registration'

    def _peppol_register_sender_as_receiver(self):
        self.ensure_one()
        company = self.company_id

        if company.account_peppol_proxy_state != 'sender':
            # a participant can only try registering as a receiver if they are currently a sender
            peppol_state_translated = dict(company._fields['account_peppol_proxy_state'].selection)[company.account_peppol_proxy_state]
            raise UserError(
                _('Cannot register a user with a %s application', peppol_state_translated))

        edi_identification = self._get_proxy_identification(company, 'peppol')
        self._check_company_on_peppol(company, edi_identification)

        self._call_peppol_proxy(
            endpoint='/api/peppol/1/register_sender_as_receiver',
            params={
                'migration_key': company.account_peppol_migration_key,
                'supported_identifiers': list(company._peppol_supported_document_types())
            },
        )
        # once we sent the migration key over, we don't need it
        # but we need the field for future in case the user decided to migrate away from Odoo
        company.account_peppol_migration_key = False
        company.account_peppol_proxy_state = 'smp_registration'

    def _peppol_deregister_participant(self):
        self.ensure_one()

        if self.company_id.account_peppol_proxy_state == 'receiver':
            # fetch all documents and message statuses before unlinking the edi user
            # so that the invoices are acknowledged
            self._cron_peppol_get_message_status()
            self._cron_peppol_get_new_documents()
            if not tools.config['test_enable'] and not modules.module.current_test:
                self.env.cr.commit()

        if self.company_id.account_peppol_proxy_state != 'not_registered':
            self._call_peppol_proxy(endpoint='/api/peppol/1/cancel_peppol_registration')

        self.company_id.account_peppol_proxy_state = 'not_registered'
        self.company_id.account_peppol_migration_key = False
        self.unlink()

    @api.model
    def _peppol_auto_register_services(self, module):
        """Register new document types for all recipient users.

        This function should be run in the post init hook of any module that extends the supported
        document types.

        :param module: Module from which this function is being called, allows us to determine which
            document types are now supported.
        """
        receivers = self.search([
            ('proxy_type', '=', 'peppol'),
            ('company_id.account_peppol_proxy_state', '=', 'receiver')
        ])
        supported_identifiers = list(self.env['res.company']._peppol_modules_document_types().get(module, {}))
        for receiver in receivers:
            try:
                receiver._call_peppol_proxy(
                    "/api/peppol/2/add_services", {
                        'document_identifiers': supported_identifiers,
                    },
                )
            # Broad exception case, so as not to block execution of the rest of the _post_init hook.
            except (AccountEdiProxyError, UserError) as exception:
                _logger.error(
                    'Auto registration of peppol services for module: %s failed on the user: %s, with exception: %s',
                    module, receiver.edi_identification, exception,
                )

    @api.model
    def _peppol_auto_deregister_services(self, module):
        """Unregister a set of document types for all recipient users.

        This function should be run in the uninstall hook of any module that extends the supported
        document types.

        :param module: Module from which this function is being called, allows us to determine which
            document types are no longer supported.
        """
        receivers = self.search([
            ('proxy_type', '=', 'peppol'),
            ('company_id.account_peppol_proxy_state', '=', 'receiver')
        ])
        unsupported_identifiers = list(self.env['res.company']._peppol_modules_document_types().get(module, {}))
        for receiver in receivers:
            try:
                receiver._call_peppol_proxy(
                    "/api/peppol/2/remove_services", {
                        'document_identifiers': unsupported_identifiers,
                    },
                )
            except (AccountEdiProxyError, UserError) as exception:
                _logger.error(
                    'Auto deregistration of peppol services for module: %s failed on the user: %s, with exception: %s',
                    module, receiver.edi_identification, exception,
                )

    def _peppol_get_services(self):
        """Get information from the IAP regarding the Peppol services."""
        self.ensure_one()
        return self._call_peppol_proxy("/api/peppol/2/get_services")
