# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.addons.l10n_it_edi.models.account_move import WAITING_STATES

_logger = logging.getLogger(__name__)


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    proxy_type = fields.Selection(selection_add=[('l10n_it_edi', 'Italian EDI')], ondelete={'l10n_it_edi': 'cascade'})

    def _get_proxy_urls(self):
        urls = super()._get_proxy_urls()
        urls['l10n_it_edi'] = {
            'demo': False,
            'prod': 'https://l10n-it-edi.api.odoo.com',
            'test': 'https://iap-services-test.odoo.com',
        }
        return urls

    def _compute_proxy_type(self):
        # Extends account_edi_proxy_client
        super()._compute_proxy_type()
        for user in self:
            if user.company_id.country_code == 'IT':
                user.proxy_type = 'l10n_it_edi'

    def _get_proxy_identification(self, company, proxy_type):
        if proxy_type == 'l10n_it_edi':
            if not company.l10n_it_codice_fiscale:
                raise UserError(_('Please fill your codice fiscale to be able to receive invoices from FatturaPA'))
            return self.env['res.partner']._l10n_it_edi_normalized_codice_fiscale(company.l10n_it_codice_fiscale)
        return super()._get_proxy_identification(company, proxy_type)

    def _l10n_it_edi_upload(self, files):
        '''Upload files to the SdI.

        :param files:    A list of dictionary {filename, base64_xml}.
        :returns:        A dictionary.
        * message:       Message from fatturapa.
        * transactionId: The fatturapa ID of this request.
        * error:         An eventual error.
        * error_level:   Info, warning, error.
        '''
        if not files:
            return {}
        if self.edi_mode == 'demo':
            return {file_data['filename']: {'id_transaction': 'demo'} for file_data in files}

        ERRORS = {'EI01': _('Attached file is empty'),
                  'EI02': _('Service momentarily unavailable'),
                  'EI03': _('Unauthorized user')}

        server_url = self._get_server_url()
        results = self._make_request(
            f'{server_url}/api/l10n_it_edi/1/out/SdiRiceviFile',
            params={'files': files})

        for filename, vals in results.items():
            if 'error' in vals:
                results[filename]['error'] = ERRORS.get(vals.get('error'), _("Unknown error"))

        return results

    def cron_l10n_it_edi_download_and_update(self):
        """ Crons run with sudo(), with empty recordset. Remember that. """
        retrigger = False
        for proxy_user in self.search([('proxy_type', '=', 'l10n_it_edi')]):
            proxy_user = proxy_user.with_company(proxy_user.company_id)
            if proxy_user.edi_mode != 'demo':
                proxy_user._l10n_it_edi_update()
                retrigger = retrigger or proxy_user._l10n_it_edi_download()
            else:
                proxy_user._l10n_it_edi_demo_mode_update()

        # Retrigger download if there are still some on the server
        if retrigger:
            _logger.info('Retriggering "Receive invoices from the SdI"...')
            self.env.ref('l10n_it_edi.ir_cron_l10n_it_edi_download_and_update')._trigger()

    def _l10n_it_edi_download(self):
        """ Check the proxy for incoming invoices for a specified proxy user.
            :param transaction_ids: id of the SdI transaction for communication with the IAP proxy.
        """
        server_url = self._get_server_url()

        # Download invoices
        invoices_data = {}
        try:
            invoices_data = self._make_request(f'{server_url}/api/l10n_it_edi/1/in/RicezioneInvoice',
                params={'recipient_codice_fiscale': self.company_id.l10n_it_codice_fiscale})
        except AccountEdiProxyError as e:
            _logger.error('Error while receiving invoices from the SdI: %s', e)
            return False

        # Process the downoaded invoices
        processed = self._l10n_it_edi_process_downloads(invoices_data)
        if processed['proxy_acks']:
            try:
                self._make_request(
                    f'{server_url}/api/l10n_it_edi/1/ack',
                    params={'transaction_ids': processed['proxy_acks']})
            except AccountEdiProxyError as e:
                _logger.error('Error while receiving file from the SdI: %s', e)

        return processed['retrigger']

    def _l10n_it_edi_store_download(self, filename, content, key):
        """ Save an incoming file from the SdI as an attachment.
            Commits if successful.

            :param filename:       name of the file to be saved.
            :param content:        encrypted content of the file to be saved.
            :param key:            key to decrypt the file.
        """

        # Name should be unique, the invoice already exists
        Attachment = self.env['ir.attachment']
        if Attachment.search([('name', '=', filename), ('res_model', '=', 'account.move')], limit=1):
            _logger.warning('E-invoice already exists: %s', filename)
            return Attachment

        # Decrypt with the server key
        try:
            decrypted_content = self._decrypt_data(content, key)
        # pylint: disable=broad-except
        except Exception as e:
            _logger.warning("Cannot decrypt e-invoice: %s, %s", filename, e)
            return Attachment

        # Create the attachment and commit
        attachment = Attachment.create({
            'name': filename,
            'raw': decrypted_content.encode(),
            'type': 'binary'
        })
        self.env.cr.commit()

        return attachment

    def _l10n_it_edi_process_downloads(self, invoices_data):
        """ Every attachment will be committed if stored succesfully.
            Also moves will be committed one by one, even if imported incorrectly.
        """
        proxy_acks = []

        # Save the attachments
        attachments = {}
        for id_transaction, invoice_data in invoices_data.items():
            attachment = self._l10n_it_edi_store_download(invoice_data['filename'], invoice_data['file'], invoice_data['key'])
            if attachment == self.env['ir.attachment']:
                proxy_acks.append(id_transaction)
            elif attachment:
                attachments[id_transaction] = [invoice_data, attachment]

        retrigger = False
        Journal = self.env['account.journal'].with_context(default_move_type='in_invoice')
        for id_transaction, (invoice_data, attachment) in attachments.items():

            # The server has a maximum number of documents it can send at a time
            # If that maximum is reached, then we search for more
            # by re-triggering the download cron, avoiding the timeout.
            current_num = invoices_data.get('current_num', 0)
            max_num = invoice_data.get('max_num', 0)
            retrigger = retrigger or current_num == max_num > 0

            # Import the move from the attachment.
            # `_create_document_from_attachment` will create an empty move
            # then try and fill it with the content imported from the attachment.
            # Should the import fail, thanks to try..except and savepoint,
            # we will anyway end up with an empty `in_invoice` with the attachment posted on it.
            # The move will be committed anyway
            Journal._create_document_from_attachment(attachment.ids)
            self.env.cr.commit()
            proxy_acks.append(id_transaction)

        return {"retrigger": retrigger, "proxy_acks": proxy_acks}

    def _l10n_it_edi_update(self, move=None, interactive=False):
        ''' Check if the sent invoices have been processed by the SdI.
            :param move: If specified, it checks just this move.
                         If unspecified, it searches for moves needing update.
            :param interactive: If True, raises UserError(s)
                                If False, logs to the Odoo log.
        '''
        self.ensure_one()
        moves = move or self.env['account.move'].search([
            ('company_id', '=', self.company_id.id),
            ('l10n_it_edi_transaction', '!=', False),
            ('l10n_it_edi_state', 'in', WAITING_STATES)
        ])
        if self.edi_mode == 'demo':
            return moves._l10n_it_edi_demo_mode_update()

        server_url = self._get_server_url()
        try:
            updates_data = self._make_request(
                f'{server_url}/api/l10n_it_edi/1/in/TrasmissioneFatture',
                params={'ids_transaction': moves.mapped("l10n_it_edi_transaction")})

            for _id_transaction, update_data in updates_data.items():
                encrypted_update_content = update_data.get('file')
                encryption_key = update_data.get('key')
                if (encrypted_update_content and encryption_key):
                    update_data['xml_content'] = self._decrypt_data(encrypted_update_content, encryption_key)

            if (acks := moves._l10n_it_edi_update(updates_data)):
                self._make_request(
                    f'{server_url}/api/l10n_it_edi/1/ack',
                    params={'transaction_ids': acks})

        except AccountEdiProxyError as pe:
            raise UserError(_("An error occurred while contacting the Proxy Server: (%s) %s", pe.code, pe.message))
        except Exception as e:
            raise UserError(_("An error occurred while updating the invoice(s) from the Proxy Server: %s", e))
