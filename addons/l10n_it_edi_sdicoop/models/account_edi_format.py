# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _, _lt
from odoo.exceptions import UserError
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError

from lxml import etree
import base64
import logging

_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    # -------------------------------------------------------------------------
    # Import
    # -------------------------------------------------------------------------

    def _cron_receive_fattura_pa(self):
        ''' Check the proxy for incoming invoices.
        '''
        proxy_users = self.env['account_edi_proxy_client.user'].search([('edi_format_id', '=', self.env.ref('l10n_it_edi.edi_fatturaPA').id)])

        if proxy_users._get_demo_state() == 'demo':
            return

        for proxy_user in proxy_users:
            company = proxy_user.company_id
            try:
                res = proxy_user._make_request(proxy_user._get_server_url() + '/api/l10n_it_edi/1/in/RicezioneInvoice',
                                               params={'recipient_codice_fiscale': company.l10n_it_codice_fiscale})
            except AccountEdiProxyError as e:
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

                invoice = self.env.ref('l10n_it_edi.edi_fatturaPA')._create_invoice_from_xml_tree(fattura['filename'], tree)
                self.env['ir.attachment'].create({
                    'name': fattura['filename'],
                    'raw': file,
                    'type': 'binary',
                    'res_model': 'account.move',
                    'res_id': invoice.id
                })

                proxy_acks.append(id_transaction)

            if proxy_acks:
                try:
                    proxy_user._make_request(proxy_user._get_server_url() + '/api/l10n_it_edi/1/ack',
                                            params={'transaction_ids': proxy_acks})
                except AccountEdiProxyError as e:
                    _logger.error('Error while receiving file from SdiCoop: %s', e)

    # -------------------------------------------------------------------------
    # Export
    # -------------------------------------------------------------------------

    def _get_invoice_edi_content(self, move):
        #OVERRIDE
        if self.code != 'fattura_pa':
            return super()._get_invoice_edi_content(move)
        return move._export_as_xml()

    def _check_move_configuration(self, move):
        # OVERRIDE
        res = super()._check_move_configuration(move)
        if self.code != 'fattura_pa':
            return res

        res.extend(self._l10n_it_edi_check_invoice_configuration(move))

        if not self._get_proxy_user(move.company_id):
            res.append(_("You must accept the terms and conditions in the settings to use FatturaPA."))

        return res

    def _needs_web_services(self):
        self.ensure_one()
        return self.code == 'fattura_pa' or super()._needs_web_services()

    def _l10n_it_edi_is_required_for_invoice(self, invoice):
        """ _is_required_for_invoice for SdiCoop.
            OVERRIDE
        """
        return invoice.is_sale_document() and invoice.country_code == 'IT'

    def _support_batching(self, move=None, state=None, company=None):
        # OVERRIDE
        if self.code == 'fattura_pa':
            return state == 'to_send' and move.is_invoice()

        return super()._support_batching(move=move, state=state, company=company)

    def _get_batch_key(self, move, state):
        # OVERRIDE
        if self.code != 'fattura_pa':
            return super()._get_batch_key(move, state)

        return move.move_type, bool(move.l10n_it_edi_transaction)

    def _l10n_it_post_invoices_step_1(self, invoices):
        ''' Send the invoices to the proxy.
        '''
        to_return = {}

        to_send = {}
        for invoice in invoices:
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
                to_return[invoice] = {'attachment': attachment}
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

        if proxy_user._get_demo_state() == 'demo':
            responses = {filename: {'id_transaction': 'demo'} for invoice in invoices}
        else:
            try:
                responses = self._l10n_it_edi_upload([i['data'] for i in to_send.values()], proxy_user)
            except AccountEdiProxyError as e:
                return {invoice: {'error': e.message, 'blocking_level': 'error'} for invoice in invoices}

        for filename, response in responses.items():
            invoice = to_send[filename]['invoice']
            to_return[invoice] = response
            if 'id_transaction' in response:
                invoice.l10n_it_edi_transaction = response['id_transaction']
                to_return[invoice].update({
                    'error': _('The invoice was successfully transmitted to the Public Administration and we are waiting for confirmation.'),
                    'blocking_level': 'info',
                })
        return to_return

    def _l10n_it_post_invoices_step_2(self, invoices):
        ''' Check if the sent invoices have been processed by FatturaPA.
        '''
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
            except AccountEdiProxyError as e:
                return {invoice: {'error': e.message, 'blocking_level': 'error'} for invoice in invoices}

        proxy_acks = []
        for id_transaction, response in responses.items():
            invoice = to_check[id_transaction]
            if 'error' in response:
                to_return[invoice] = response
                continue

            state = response['state']
            if state == 'awaiting_outcome':
                to_return[invoice] = {
                    'error': _('The invoice was successfully transmitted to the Public Administration and we are waiting for confirmation'),
                    'blocking_level': 'info',
                }
                proxy_acks.append(id_transaction)
                continue
            elif state == 'not_found':
                # Invoice does not exist on proxy. Either it does not belong to this proxy_user or it was not created correctly when
                # it was sent to the proxy.
                to_return[invoice] = {'error': _('You are not allowed to check the status of this invoice.'), 'blocking_level': 'error'}
                continue

            if not response.get('file'): # It means there is no status update, so we can skip it
                document = invoice.edi_document_ids.filtered(lambda d: d.edi_format_id.code == 'fattura_pa')
                to_return[invoice] = {'error': document.error, 'blocking_level': document.blocking_level}
                continue
            xml = proxy_user._decrypt_data(response['file'], response['key'])
            response_tree = etree.fromstring(xml)
            if state == 'ricevutaConsegna':
                if invoice._is_commercial_partner_pa():
                    to_return[invoice] = {'error': _('The invoice has been succesfully transmitted. The addressee has 15 days to accept or reject it.')}
                else:
                    to_return[invoice] = {'attachment': invoice.l10n_it_edi_attachment_id, 'success': True}
            elif state == 'notificaScarto':
                errors = [element.find('Descrizione').text for element in response_tree.xpath('//Errore')]
                to_return[invoice] = {'error': self._format_error_message(_('The invoice has been refused by the Exchange System'), errors), 'blocking_level': 'error'}
                invoice.l10n_it_edi_transaction = False
            elif state == 'notificaMancataConsegna':
                if invoice._is_commercial_partner_pa():
                    to_return[invoice] = {'error': _(
                        'The invoice has been issued, but the delivery to the Public Administration'
                        ' has failed. The Exchange System will contact them to report the problem'
                        ' and request that they provide a solution.'
                        ' During the following 10 days, the Exchange System will try to forward the'
                        ' FatturaPA file to the Public Administration in question again.'
                        ' Should this also fail, the System will notify Odoo of the failed delivery,'
                        ' and you will be required to send the invoice to the Administration'
                        ' through another channel, outside of the Exchange System.')}
                else:
                    to_return[invoice] = {'success': True, 'attachment': invoice.l10n_it_edi_attachment_id}
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
                    to_return[invoice] = {'attachment': invoice.l10n_it_edi_attachment_id, 'success': True}
                else:  # ECO2
                    to_return[invoice] = {'error': _('The invoice was refused by the addressee.'), 'blocking_level': 'error'}
            elif state == 'NotificaDecorrenzaTermini':
                to_return[invoice] = {'attachment': invoice.l10n_it_edi_attachment_id, 'success': True}
            proxy_acks.append(id_transaction)

        if proxy_acks:
            try:
                proxy_user._make_request(proxy_user._get_server_url() + '/api/l10n_it_edi/1/ack',
                                        params={'transaction_ids': proxy_acks})
            except AccountEdiProxyError as e:
                # Will be ignored and acked again next time.
                _logger.error('Error while acking file to SdiCoop: %s', e)

        return to_return

    def _post_fattura_pa(self, invoices):
        # OVERRIDE
        if not invoices[0].l10n_it_edi_transaction:
            return self._l10n_it_post_invoices_step_1(invoices)
        else:
            return self._l10n_it_post_invoices_step_2(invoices)

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

        result = proxy_user._make_request(proxy_user._get_server_url() + '/api/l10n_it_edi/1/out/SdiRiceviFile', params={'files': files})

        # Translate the errors.
        for filename in result.keys():
            if 'error' in result[filename]:
                result[filename] = ERRORS.get(result[filename]['error'], {'error': result[filename]['error'], 'blocking_level': 'error'})

        return result
