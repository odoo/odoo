# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import zipfile
import io
import logging

from lxml import etree

from odoo import api, models, tools, _
from odoo.tests.common import Form


_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _name = 'mail.thread'
    _inherit = 'mail.thread'

    @api.model
    def message_route(self, message, message_dict, model=None, thread_id=None, custom_values=None):
        email_from = tools.decode_message_header(message, 'From')
        email_return_path = tools.decode_message_header(message, 'Return-Path')
        email_reply_to = tools.decode_message_header(message, 'Reply-To')
        if any('@pec.fatturapa.it' in x for x in [email_from, email_return_path, email_reply_to]):
            for attachment in message_dict['attachments']:
                split_attachment = attachment.fname.rpartition('.')
                if len(split_attachment) < 3:
                    _logger.info('Error when parsing E-invoice filename: %s', attachment.fname)
                    continue
                attachment_name = split_attachment[0]
                attachment_ext = split_attachment[2]
                split_underscore = attachment_name.rsplit('_', 2)
                if len(split_underscore) < 2:
                    _logger.info('Error when parsing E-invoice filename: %s', attachment.fname)
                    continue

                if attachment_ext != 'zip':
                    if split_underscore[1] in ['RC', 'NS', 'MC', 'MT', 'EC', 'SE', 'NE', 'DT']:
                        # we have a receipt
                        self._message_receipt_invoice(split_underscore[1], attachment)
                    else:
                        # we have a new E-invoice
                        self._create_invoice_from_mail(message_dict, attachment)
                else:
                    if split_underscore[1] == 'AT':
                        # Attestazione di avvenuta trasmissione della fattura con impossibilità di recapito
                        self._message_AT_invoice(attachment)
                    else:
                        _logger.info('New E-invoice in zip file: %s', attachment.fname)
                        self._create_invoice_from_mail_with_zip(message_dict, attachment)

            del message_dict['attachments']
            del message_dict['cc']
            del message_dict['from']
            del message_dict['to']
            message_dict['record_name'] = message_dict['subject']
            self.env['mail.message'].with_context(message_create_from_mail_mail=True).create(message_dict)
            return []
        return super(MailThread, self).message_route(message, message_dict, model=model, thread_id=thread_id, custom_values=custom_values)

    def _create_invoice_from_mail(self, message_dict, attachment):
        if self.env['account.invoice'].search([('doc_unique_name', '=', attachment.fname)], limit=1):
            # invoice already exist
            _logger.info('E-invoice already exist: %s', attachment.fname)
            return

        message_dict['model'] = 'account.invoice'
        message_dict['record_name'] = attachment.fname

        self = self.with_context(default_journal_id=(self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)).id)
        invoice_form = Form(self.env['account.invoice'], view='account.invoice_supplier_form')
        invoice = invoice_form.save()
        invoice.doc_unique_name = attachment.fname
        invoice.send_state = "new"

        message_dict['res_id'] = invoice.id
        _, attachment_id = self._message_post_process_attachments([attachment], [], message_dict)[0]
        invoice.message_post(attachment_ids=[attachment_id])

        del message_dict['model']
        del message_dict['res_id']
        _logger.info('New E-invoice: %s', attachment.fname)

    def _create_invoice_from_mail_with_zip(self, message_dict, attachment_zip):
        with zipfile.ZipFile(io.BytesIO(attachment_zip.content)) as z:
            for attachment_name in z.namelist():
                if self.env['account.invoice'].search([('doc_unique_name', '=', attachment_name)], limit=1):
                    # invoice already exist
                    _logger.info('E-invoice in zip file (%s) already exist: %s', attachment_zip.fname, attachment_name)
                    continue
                attachment = z.open(attachment_name).read()

                message_dict['model'] = 'account.invoice'
                message_dict['record_name'] = attachment_name

                self = self.with_context(default_journal_id=(self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)).id)
                invoice_form = Form(self.env['account.invoice'], view='account.invoice_supplier_form')
                invoice = invoice_form.save()
                invoice.doc_unique_name = attachment.fname
                invoice.send_state = "new"

                message_dict['res_id'] = invoice.id
                _, attachment_id = self._message_post_process_attachments(
                    [[attachment_name, attachment.decode('utf-8')]], [], message_dict)[0]
                invoice.message_post(attachment_ids=[attachment_id])

                del message_dict['model']
                del message_dict['res_id']
                _logger.info('New E-invoice: %s', attachment_name)

    def _message_AT_invoice(self, attachment_zip):
        with zipfile.ZipFile(io.BytesIO(attachment_zip.content)) as z:
            for attachment_name in z.namelist():
                split_name_attachment = attachment_name.rpartition('.')
                if len(split_name_attachment) < 3:
                    continue
                split_underscore = split_name_attachment[0].rsplit('_', 2)
                if len(split_underscore) < 2:
                    continue
                if split_underscore[1] == 'AT':
                    attachment = z.open(attachment_name).read()
                    _logger.info('New AT receipt for: %s', split_underscore[0])
                    try:
                        tree = etree.fromstring(attachment)
                    except:
                        _logger.info('Error in decoding new receipt file: %s', attachment_name)
                        return

                    elements = tree.xpath('//NomeFile', namespaces=tree.nsmap)
                    if elements and elements[0].text:
                        filename = elements[0].text
                    else:
                        return

                    related_invoice = self.env['account.invoice'].search([
                        ('doc_unique_name', '=', filename)])
                    if not related_invoice:
                        _logger.info('Error: invoice not found for receipt file: %s', filename)
                        return

                    related_invoice.send_state = 'failed_delivery'
                    info = self._return_multi_line_xml(tree, ['//IdentificativoSdI', '//DataOraRicezione', '//MessageId', '//PecMessageId', '//Note'])
                    related_invoice.message_post(
                        body=(_("ES certify that it has received the invoice and that the file \
                        could not be delivered to the addressee. <br/>%s") % (info))
                    )

    def _message_receipt_invoice(self, receipt_type, attachment):
        try:
            tree = etree.fromstring(attachment.content)
        except:
            _logger.info('Error in decoding new receipt file: %s', attachment.fname)
            return {}

        elements = tree.xpath('//NomeFile', namespaces=tree.nsmap)
        if elements and elements[0].text:
            filename = elements[0].text
        else:
            return {}

        if receipt_type == 'RC':
            # Delivery receipt
            # This is the receipt sent by the ES to the transmitting subject to communicate
            # delivery of the file to the addressee
            related_invoice = self.env['account.invoice'].search([
                ('doc_unique_name', '=', filename),
                ('send_state', '=', 'sent')])
            if not related_invoice:
                _logger.info('Error: invoice not found for receipt file: %s', attachment.fname)
                return
            related_invoice.send_state = 'delivered'
            info = self._return_multi_line_xml(tree, ['//IdentificativoSdI', '//DataOraRicezione', '//DataOraConsegna', '//Note'])
            related_invoice.message_post(
                body=(_("E-Invoice is delivery to the destinatory:<br/>%s") % (info))
            )

        elif receipt_type == 'NS':
            # Rejection notice
            # This is the receipt sent by the ES to the transmitting subject if one or more of
            # the checks carried out by the ES on the file received do not have a successful result.
            related_invoice = self.env['account.invoice'].search([
                ('doc_unique_name', '=', filename),
                ('send_state', '=', 'sent')])
            if not related_invoice:
                _logger.info('Error: invoice not found for receipt file: %s', attachment.fname)
                return
            related_invoice.send_state = 'invalid'
            error = self._return_error_xml(tree)
            related_invoice.message_post(
                body=(_("Errors in the E-Invoice :<br/>%s") % (error))
            )
            activity_vals = {
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'user_id': related_invoice.user_id.id if related_invoice.user_id else self.env.user.id
            }
            related_invoice.activity_schedule(summary='Rejection notice', **activity_vals)

        elif receipt_type == 'MC':
            # Failed delivery notice
            # This is the receipt sent by the ES to the transmitting subject if the file is not
            # delivered to the addressee.
            related_invoice = self.env['account.invoice'].search([
                ('doc_unique_name', '=', filename),
                ('send_state', '=', 'sent')])
            if not related_invoice:
                _logger.info('Error: invoice not found for receipt file: %s', attachment.fname)
                return
            info = self._return_multi_line_xml(tree, [
                '//IdentificativoSdI',
                '//DataOraRicezione',
                '//Descrizione',
                '//MessageId',
                '//Note'])
            related_invoice.message_post(
                body=(_("The E-invoice is not delivered to the addressee. The Exchange System is\
                unable to deliver the file to the Public Administration. The Exchange System will\
                contact the PA to report the problem and request that they provide a solution. \
                During the following 15 days, the Exchange System will try to forward the FatturaPA\
                file to the Administration in question again. More informations:<br/>%s") % (info))
            )

        elif receipt_type == 'NE':
            # Outcome notice
            # This is the receipt sent by the ES to the invoice sender to communicate the result
            # (acceptance or refusal of the invoice) of the checks carried out on the document by
            # the addressee.
            related_invoice = self.env['account.invoice'].search([
                ('doc_unique_name', '=', filename),
                ('send_state', '=', 'delivered')])
            if not related_invoice:
                _logger.info('Error: invoice not found for receipt file: %s', attachment.fname)
                return
            elements = tree.xpath('//Esito', namespaces=tree.nsmap)
            if elements and elements[0].text:
                if elements[0].text == 'EC01':
                    related_invoice.send_state = 'delivered_accepted'
                elif elements[0].text == 'EC02':
                    related_invoice.send_state = 'delivered_refused'

            info = self._return_multi_line_xml(tree,
                                               ['//Esito',
                                                '//Descrizione',
                                                '//IdentificativoSdI',
                                                '//DataOraRicezione',
                                                '//DataOraConsegna',
                                                '//Note'
                                               ])
            related_invoice.message_post(
                body=(_("Outcome notice: %s<br/>%s") % (related_invoice.send_state, info))
            )
            if related_invoice.send_state == 'delivered_refused':
                activity_vals = {
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'user_id': related_invoice.user_id.id if related_invoice.user_id else self.env.user.id
                }
                related_invoice.activity_schedule(summary='Outcome notice: Refused', **activity_vals)

        elif receipt_type == 'MT':
            # Metadata file
            # This is the file sent by the ES to the addressee together with the invoice file,
            # containing the main reference data of the file useful for processing, including
            # the IdentificativoSDI.
            elements = tree.xpath('//TentativiInvio', namespaces=tree.nsmap)
            if elements and elements[0].text:
                tentativi = elements[0].text
                if tentativi > 1:
                    _logger.info('[%s] Tentativi Invio: %s', filename, tentativi)

        elif receipt_type == 'DT':
            # Deadline passed notice
            # This is the receipt sent by the ES to both the invoice sender and the invoice
            # addressee to communicate the expiry of the maximum term for communication of
            # acceptance/refusal.
            related_invoice = self.env['account.invoice'].search([
                ('doc_unique_name', '=', filename), ('send_state', '=', 'delivered')])
            if not related_invoice:
                _logger.info('Error: invoice not found for receipt file: %s', attachment.fname)
                return
            related_invoice.send_state = 'delivered_expired'
            info = self._return_multi_line_xml(tree, [
                '//Descrizione',
                '//IdentificativoSdI',
                '//Note'])
            related_invoice.message_post(
                body=(_("Expiration of the maximum term for communication of acceptance/refusal:\
                 %s<br/>%s") % (filename, info))
            )

    def _return_multi_line_xml(self, tree, element_tags):
        output_str = "<ul>"

        for element_tag in element_tags:
            elements = tree.xpath(element_tag, namespaces=tree.nsmap)
            if not elements:
                continue
            for element in elements:
                text = " ".join(element.text.split())
                if text:
                    output_str += "<li>%s: %s</li>" % (element.tag, text)
        return output_str + "</ul>"

    def _return_error_xml(self, tree):
        output_str = "<ul>"

        elements = tree.xpath('//Errore', namespaces=tree.nsmap)
        if not elements:
            return
        for element in elements:
            descrizione = " ".join(element[1].text.split())
            if descrizione:
                output_str += "<li>Errore %s: %s</li>" % (element[0].text, descrizione)
        return output_str + "</ul>"
