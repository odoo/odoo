# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _, _lt
from odoo.exceptions import UserError
from odoo.addons.edi_proxy_client.models.edi_proxy_user import EdiProxyError

from lxml import etree
import base64
import logging

_logger = logging.getLogger(__name__)


class EdiFormat(models.Model):
    _inherit = 'edi.format'

    def _get_edi_format_settings(self, document=None, stage=None, flow_type=None):
        self.ensure_one()
        if self.code != 'fattura_pa':
            return super()._get_edi_format_settings(document, stage, flow_type)
        return {
            'needs_web_services': True,
            'attachments_required_in_mail': False,
            'batching_key': (document.move_type, bool(document.l10n_it_edi_transaction)) if document and document.is_invoice() and stage == 'to_send' else False,
            'document_needs_embedding': document and document.is_sale_document() and document.state != 'draft',
            'stages': {
                'send': {
                    'Upload to SDI': {
                        'new_state': 'to_send',
                        'action': self._l10n_it_post_invoices_step_1,
                    },
                    'Validate invoice': {
                        'action': self._l10n_it_post_invoices_step_2,
                    },
                    'Invoice issued and accepted': {
                        'new_state': 'sent',
                        'make_attachments_official': True,
                    },
                }
            }
        }

    # -------------------------------------------------------------------------
    # Import
    # -------------------------------------------------------------------------

    def _cron_receive_fattura_pa(self):
        ''' Check the proxy for incoming invoices.
        '''
        proxy_users = self.env['edi_proxy_client.user'].search([('edi_format_id', '=', self.env.ref('l10n_it_edi.edi_fatturaPA').id)])

        if proxy_users._get_demo_state() == 'demo':
            return

        for proxy_user in proxy_users:
            company = proxy_user.company_id
            try:
                res = proxy_user._make_request(proxy_user._get_server_url() + '/api/l10n_it_edi/1/in/RicezioneInvoice',
                                               params={'recipient_codice_fiscale': company.l10n_it_codice_fiscale})
            except EdiProxyError as e:
                _logger.error('Error while receiving file from SdiCoop: %s', e)

            proxy_acks = []
            for id_transaction, fattura in res.items():
                if self.env['ir.attachment'].search([('name', '=', fattura['filename']), ('res_model', '=', 'account.move')], limit=1):
                    # name should be unique, the invoice already exists
                    _logger.info('E-invoice already exist: %s', fattura['filename'])
                    proxy_acks.append(id_transaction)
                    continue

                file = proxy_user._decrypt_data(fattura['file'], fattura['key'])

                try:
                    tree = etree.fromstring(file)
                except Exception:
                    # should not happen as the file has been checked by SdiCoop
                    _logger.info('Received file badly formatted, skipping: \n %s', file)
                    continue

                invoice = self.env['account.move'].create({'move_type': 'in_invoice'})
                attachment = self.env['ir.attachment'].create({
                    'name': fattura['filename'],
                    'raw': file,
                    'type': 'binary',
                    'res_model': 'account.move',
                    'res_id': invoice.id
                })
                if not self.env.context.get('test_skip_commit'):
                    self.env.cr.commit() #In case something fails after, we still have the attachment
                # So that we don't delete the attachment when deleting the invoice
                attachment.res_id = False
                attachment.res_model = False
                invoice.unlink()
                invoice = self.env.ref('l10n_it_edi.edi_fatturaPA')._create_invoice_from_xml_tree(fattura['filename'], tree)
                attachment.write({'res_model': 'account.move',
                                  'res_id': invoice.id})
                proxy_acks.append(id_transaction)
                if not self.env.context.get('test_skip_commit'):
                    self.env.cr.commit()

            if proxy_acks:
                try:
                    proxy_user._make_request(proxy_user._get_server_url() + '/api/l10n_it_edi/1/ack',
                                            params={'transaction_ids': proxy_acks})
                except EdiProxyError as e:
                    _logger.error('Error while receiving file from SdiCoop: %s', e)

    # -------------------------------------------------------------------------
    # Export
    # -------------------------------------------------------------------------

    # def _get_invoice_edi_content(self, move):
    #     #OVERRIDE todo vin
    #     if self.code != 'fattura_pa':
    #         return super()._get_invoice_edi_content(move)
    #     return move._export_as_xml()

    def _check_document_configuration(self, move):
        # OVERRIDE
        res = super()._check_document_configuration(move)
        if self.code != 'fattura_pa':
            return res

        res.extend(self._l10n_it_edi_check_invoice_configuration(move))

        if not self._get_proxy_user(move.company_id):
            res.append(_("You must accept the terms and conditions in the settings to use FatturaPA."))

        return res

    def _l10n_it_edi_is_required_for_invoice(self, document, document_type):
        """ _is_required_for_invoice for SdiCoop.
            OVERRIDE
        """
        return document_type in ('invoice', 'payment') and document.is_sale_document() and document.country_code == 'IT'

    def _l10n_it_post_invoices_step_1(self, flows):
        ''' Send the invoices to the proxy.
        '''
        to_return = {}

        to_send = {}
        invoices = flows._get_documents()
        for flow in flows:
            invoice = invoices.filtered(lambda i: i.id == flow.res_id)
            xml = "<?xml version='1.0' encoding='UTF-8'?>" + str(invoice._export_as_xml())
            filename = self._l10n_it_edi_generate_electronic_invoice_filename(invoice)
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'res_id': invoice.id,
                'res_model': invoice._name,
                'raw': xml.encode(),
                'description': _('Italian invoice: %s', invoice.move_type),
                'type': 'binary',
            })
            invoice.l10n_it_edi_attachment_id = attachment

            if invoice._is_commercial_partner_pa():
                invoice.message_post(
                    body=(_("Invoices for PA are not managed by Odoo, you can download the document and send it on your own."))
                )
                to_return[invoice.id] = {'success': True, 'attachment': attachment}
            else:
                to_send[filename] = {
                    'invoice': invoice,
                    'data': {'filename': filename, 'xml': base64.b64encode(xml.encode()).decode()}}

        company = invoices.company_id
        proxy_user = self._get_proxy_user(company)
        if not proxy_user:  # proxy user should exist, because there is a check in _check_move_configuration
            return {invoice: {
                'error': _("You must accept the terms and conditions in the settings to use FatturaPA."),
                'blocking_level': 'error'} for invoice in invoices}

        responses = {}
        if proxy_user._get_demo_state() == 'demo':
            responses = {i['data']['filename']: {'id_transaction': 'demo'} for i in to_send.values()}
        else:
            try:
                responses = self._l10n_it_edi_upload([i['data'] for i in to_send.values()], proxy_user)
            except EdiProxyError as e:
                return {invoice: {'error': e.message, 'blocking_level': 'error'} for invoice in invoices}

        for filename, response in responses.items():
            invoice = to_send[filename]['invoice']
            to_return[invoice.id] = response
            if 'id_transaction' in response:
                invoice.l10n_it_edi_transaction = response['id_transaction']
                to_return[invoice.id].update({
                    'error': _('The invoice was sent to FatturaPA, but we are still awaiting a response. Click the link above to check for an update.'),
                    'blocking_level': 'info',
                })
        return to_return

    def _l10n_it_post_invoices_step_2(self, flows):
        ''' Check if the sent invoices have been processed by FatturaPA.
        '''
        invoices = flows._get_documents()
        to_check = {i.l10n_it_edi_transaction: i for i in invoices}
        to_return = {}
        company = invoices.company_id
        proxy_user = self._get_proxy_user(company)
        if not proxy_user:  # proxy user should exist, because there is a check in _check_move_configuration
            return {invoice: {
                'error': _("You must accept the terms and conditions in the settings to use FatturaPA."),
                'blocking_level': 'error'} for invoice in invoices}

        if proxy_user._get_demo_state() == 'demo':
            # simulate success and bypass ack
            return {invoice: {'attachment': invoice.l10n_it_edi_attachment_id} for invoice in invoices}
        else:
            try:
                responses = proxy_user._make_request(proxy_user._get_server_url() + '/api/l10n_it_edi/1/in/TrasmissioneFatture',
                                                    params={'ids_transaction': list(to_check.keys())})
            except EdiProxyError as e:
                return {invoice: {'error': e.message, 'blocking_level': 'error'} for invoice in invoices}

        proxy_acks = []
        for id_transaction, response in responses.items():
            invoice = to_check[id_transaction]
            if 'error' in response:
                to_return[invoice.id] = response
                continue

            state = response['state']
            if state == 'awaiting_outcome':
                to_return[invoice.id] = {
                    'error': _('The invoice was sent to FatturaPA, but we are still awaiting a response. Click the link above to check for an update.'),
                    'blocking_level': 'info',
                }
                proxy_acks.append(id_transaction)
                continue
            elif state == 'not_found':
                # Invoice does not exist on proxy. Either it does not belong to this proxy_user or it was not created correctly when
                # it was sent to the proxy.
                to_return[invoice.id] = {'error': _('You are not allowed to check the status of this invoice.'), 'blocking_level': 'error'}
                continue

            if not response.get('file'): # It means there is no status update, so we can skip it
                document = invoice.edi_document_ids.filtered(lambda d: d.edi_format_id.code == 'fattura_pa')
                to_return[invoice.id] = {'error': document.error, 'blocking_level': document.blocking_level}
                continue
            xml = proxy_user._decrypt_data(response['file'], response['key'])
            response_tree = etree.fromstring(xml)
            if state == 'ricevutaConsegna':
                if invoice._is_commercial_partner_pa():
                    to_return[invoice.id] = {'error': _('The invoice has been succesfully transmitted. The addressee has 15 days to accept or reject it.')}
                else:
                    to_return[invoice.id] = {'attachment': invoice.l10n_it_edi_attachment_id, 'success': True}
            elif state == 'notificaScarto':
                elements = response_tree.xpath('//Errore')
                error_codes = [element.find('Codice').text for element in elements]
                errors = [element.find('Descrizione').text for element in elements]
                # Duplicated invoice
                if '00404' in error_codes:
                    idx = error_codes.index('00404')
                    invoice.message_post(body=_(
                        'This invoice number had already been submitted to the SdI, so it is'
                        ' set as Sent. Please verify that the system is correctly configured,'
                        ' because the correct flow does not need to send the same invoice'
                        ' twice for any reason.\n'
                        ' Original message from the SDI: %s', errors[idx]))
                    to_return[invoice.id] = {'attachment': invoice.l10n_it_edi_attachment_id, 'success': True}
                else:
                    # Add helpful text if duplicated filename error
                    if '00002' in error_codes:
                        idx = error_codes.index('00002')
                        errors[idx] = _(
                            'The filename is duplicated. Try again (or adjust the FatturaPA Filename sequence).'
                            ' Original message from the SDI: %s', [errors[idx]]
                        )
                    to_return[invoice.id] = {'error': self._format_error_message(_('The invoice has been refused by the Exchange System'), errors), 'blocking_level': 'error'}
                    invoice.l10n_it_edi_transaction = False
            elif state == 'notificaMancataConsegna':
                if invoice._is_commercial_partner_pa():
                    to_return[invoice.id] = {'error': _(
                        'The invoice has been issued, but the delivery to the Public Administration'
                        ' has failed. The Exchange System will contact them to report the problem'
                        ' and request that they provide a solution.'
                        ' During the following 10 days, the Exchange System will try to forward the'
                        ' FatturaPA file to the Public Administration in question again.'
                        ' Should this also fail, the System will notify Odoo of the failed delivery,'
                        ' and you will be required to send the invoice to the Administration'
                        ' through another channel, outside of the Exchange System.')}
                else:
                    to_return[invoice.id] = {'success': True, 'attachment': invoice.l10n_it_edi_attachment_id}
                    invoice._message_log(body=_(
                        'The invoice has been issued, but the delivery to the Addressee has'
                        ' failed. You will be required to send a courtesy copy of the invoice'
                        ' to your customer through another channel, outside of the Exchange'
                        ' System, and promptly notify him that the original is deposited'
                        ' in his personal area on the portal "Invoices and Fees" of the'
                        ' Revenue Agency.'))
            elif state == 'notificaEsito':
                outcome = response_tree.find('Esito').text
                if outcome == 'EC01':
                    to_return[invoice.id] = {'attachment': invoice.l10n_it_edi_attachment_id, 'success': True}
                else:  # ECO2
                    to_return[invoice.id] = {'error': _('The invoice was refused by the addressee.'), 'blocking_level': 'error'}
            elif state == 'NotificaDecorrenzaTermini':
                to_return[invoice.id] = {'attachment': invoice.l10n_it_edi_attachment_id, 'success': True}
            proxy_acks.append(id_transaction)

        if proxy_acks:
            try:
                proxy_user._make_request(proxy_user._get_server_url() + '/api/l10n_it_edi/1/ack',
                                        params={'transaction_ids': proxy_acks})
            except EdiProxyError as e:
                # Will be ignored and acked again next time.
                _logger.error('Error while acking file to SdiCoop: %s', e)

        return to_return

    # -------------------------------------------------------------------------
    # Proxy methods
    # -------------------------------------------------------------------------

    def _get_proxy_identification(self, company):
        if self.code != 'fattura_pa':
            return super()._get_proxy_identification()

        if not company.l10n_it_codice_fiscale:
            raise UserError(_('Please fill your codice fiscale to be able to receive invoices from FatturaPA'))

        return self.env['res.partner']._l10n_it_normalize_codice_fiscale(company.l10n_it_codice_fiscale)

    def _l10n_it_edi_upload(self, files, proxy_user):
        '''Upload files to fatturapa.

        :param files:    A list of dictionary {filename, base64_xml}.
        :returns:        A dictionary.
        * message:       Message from fatturapa.
        * transactionId: The fatturapa ID of this request.
        * error:         An eventual error.
        * error_level:   Info, warning, error.
        '''
        ERRORS = {
            'EI01': {'error': _lt('Attached file is empty'), 'blocking_level': 'error'},
            'EI02': {'error': _lt('Service momentarily unavailable'), 'blocking_level': 'warning'},
            'EI03': {'error': _lt('Unauthorized user'), 'blocking_level': 'error'},
        }

        if not files:
            return {}

        result = proxy_user._make_request(proxy_user._get_server_url() + '/api/l10n_it_edi/1/out/SdiRiceviFile', params={'files': files})

        # Translate the errors.
        for filename in result.keys():
            if 'error' in result[filename]:
                result[filename] = ERRORS.get(result[filename]['error'], {'error': result[filename]['error'], 'blocking_level': 'error'})

        return result
