# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import zipfile
import io
import re
import logging
import email
import dateutil
import pytz
import base64
try:
    from xmlrpc import client as xmlrpclib
except ImportError:
    import xmlrpclib


from lxml import etree
from datetime import datetime

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError


_logger = logging.getLogger(__name__)

class FetchmailServer(models.Model):
    _name = 'fetchmail.server'
    _inherit = 'fetchmail.server'

    l10n_it_is_pec = fields.Boolean('PEC server', help="If PEC Server, only mail from '...@pec.fatturapa.it' will be processed.")
    l10n_it_last_uid = fields.Integer(string='Last message UID', default=1)

    @api.constrains('l10n_it_is_pec', 'server_type')
    def _check_pec(self):
        for record in self:
            if record.l10n_it_is_pec and record.server_type != 'imap':
                raise ValidationError(_("PEC mail server must be of type IMAP."))

    def fetch_mail(self):
        """ WARNING: meant for cron usage only - will commit() after each email! """

        MailThread = self.env['mail.thread']
        for server in self.filtered(lambda s: s.l10n_it_is_pec):
            _logger.info('start checking for new emails on %s PEC server %s', server.server_type, server.name)

            count, failed = 0, 0
            imap_server = None
            try:
                imap_server = server.connect()
                imap_server.select()

                result, data = imap_server.uid('search', None, '(FROM "@pec.fatturapa.it")', '(UID %s:*)' % (server.l10n_it_last_uid))
                new_max_uid = server.l10n_it_last_uid
                for uid in data[0].split():
                    if int(uid) <= server.l10n_it_last_uid:
                        # We get always minimum 1 message.  If no new message, we receive the newest already managed.
                        continue

                    result, data = imap_server.uid('fetch', uid, '(RFC822)')

                    if not data[0]:
                        continue
                    message = data[0][1]

                    # To leave the mail in the state in which they were.
                    if "Seen" not in data[1].decode("utf-8"):
                        imap_server.uid('STORE', uid, '+FLAGS', '\\Seen')
                    else:
                        imap_server.uid('STORE', uid, '-FLAGS', '\\Seen')

                    # See details in message_process() in mail_thread.py
                    if isinstance(message, xmlrpclib.Binary):
                        message = bytes(message.data)
                    if isinstance(message, str):
                        message = message.encode('utf-8')
                    msg_txt = email.message_from_bytes(message)

                    try:
                        self._attachment_invoice(msg_txt)
                        new_max_uid = max(new_max_uid, int(uid))
                    except Exception:
                        _logger.info('Failed to process mail from %s server %s.', server.server_type, server.name, exc_info=True)
                        failed += 1
                    self._cr.commit()
                    count += 1
                server.write({'l10n_it_last_uid': new_max_uid})
                _logger.info("Fetched %d email(s) on %s server %s; %d succeeded, %d failed.", count, server.server_type, server.name, (count - failed), failed)
            except Exception:
                _logger.info("General failure when trying to fetch mail from %s server %s.", server.server_type, server.name, exc_info=True)
            finally:
                if imap_server:
                    imap_server.close()
                    imap_server.logout()
                server.write({'date': fields.Datetime.now()})
        return super(FetchmailServer, self.filtered(lambda s: not s.l10n_it_is_pec)).fetch_mail()

    def _attachment_invoice(self, msg_txt):
        parsed_values = self.env['mail.thread']._message_parse_extract_payload(msg_txt)
        body, attachments = parsed_values['body'], parsed_values['attachments']
        from_address = tools.decode_smtp_header(msg_txt.get('from'))
        for attachment in attachments:
            split_attachment = attachment.fname.rpartition('.')
            if len(split_attachment) < 3:
                _logger.info('E-invoice filename not compliant: %s', attachment.fname)
                continue
            attachment_name = split_attachment[0]
            attachment_ext = split_attachment[2]
            split_underscore = attachment_name.rsplit('_', 2)
            if len(split_underscore) < 2:
                _logger.info('E-invoice filename not compliant: %s', attachment.fname)
                continue

            if attachment_ext != 'zip':
                if split_underscore[1] in ['RC', 'NS', 'MC', 'MT', 'EC', 'SE', 'NE', 'DT']:
                    # we have a receipt
                    self._message_receipt_invoice(split_underscore[1], attachment)
                elif re.search("([A-Z]{2}[A-Za-z0-9]{2,28}_[A-Za-z0-9]{0,5}.(xml.p7m|xml))", attachment.fname):
                    # we have a new E-invoice
                    self._create_invoice_from_mail(attachment.content, attachment.fname, from_address)
            else:
                if split_underscore[1] == 'AT':
                    # Attestazione di avvenuta trasmissione della fattura con impossibilità di recapito
                    self._message_AT_invoice(attachment)
                else:
                    _logger.info('New E-invoice in zip file: %s', attachment.fname)
                    self._create_invoice_from_mail_with_zip(attachment, from_address)

    def _create_invoice_from_mail(self, att_content, att_name, from_address):
        if self.env['account.move'].search([('l10n_it_einvoice_name', '=', att_name)], limit=1):
            # invoice already exist
            _logger.info('E-invoice already exist: %s', att_name)
            return

        invoice_attachment = self.env['ir.attachment'].create({
                'name': att_name,
                'datas': base64.encodestring(att_content),
                'type': 'binary',
                })

        try:
            tree = etree.fromstring(att_content)
        except Exception:
            raise UserError(_('The xml file is badly formatted : {}').format(att_name))

        invoice = self.env['account.move']._import_xml_invoice(tree)
        invoice.l10n_it_send_state = "new"
        invoice.source_email = from_address
        self._cr.commit()

        _logger.info('New E-invoice: %s', att_name)


    def _create_invoice_from_mail_with_zip(self, attachment_zip, from_address):
        with zipfile.ZipFile(io.BytesIO(attachment_zip.content)) as z:
            for att_name in z.namelist():
                if self.env['account.move'].search([('l10n_it_einvoice_name', '=', att_name)], limit=1):
                    # invoice already exist
                    _logger.info('E-invoice in zip file (%s) already exist: %s', attachment_zip.fname, att_name)
                    continue
                att_content = z.open(att_name).read()

                self._create_invoice_from_mail(att_content, att_name, from_address)

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

                    elements = tree.xpath('//NomeFile')
                    if elements and elements[0].text:
                        filename = elements[0].text
                    else:
                        return

                    related_invoice = self.env['account.move'].search([
                        ('l10n_it_einvoice_name', '=', filename)])
                    if not related_invoice:
                        _logger.info('Error: invoice not found for receipt file: %s', filename)
                        return

                    related_invoice.l10n_it_send_state = 'failed_delivery'
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

        elements = tree.xpath('//NomeFile')
        if elements and elements[0].text:
            filename = elements[0].text
        else:
            return {}

        if receipt_type == 'RC':
            # Delivery receipt
            # This is the receipt sent by the ES to the transmitting subject to communicate
            # delivery of the file to the addressee
            related_invoice = self.env['account.move'].search([
                ('l10n_it_einvoice_name', '=', filename),
                ('l10n_it_send_state', '=', 'sent')])
            if not related_invoice:
                _logger.info('Error: invoice not found for receipt file: %s', attachment.fname)
                return
            related_invoice.l10n_it_send_state = 'delivered'
            info = self._return_multi_line_xml(tree, ['//IdentificativoSdI', '//DataOraRicezione', '//DataOraConsegna', '//Note'])
            related_invoice.message_post(
                body=(_("E-Invoice is delivery to the destinatory:<br/>%s") % (info))
            )

        elif receipt_type == 'NS':
            # Rejection notice
            # This is the receipt sent by the ES to the transmitting subject if one or more of
            # the checks carried out by the ES on the file received do not have a successful result.
            related_invoice = self.env['account.move'].search([
                ('l10n_it_einvoice_name', '=', filename),
                ('l10n_it_send_state', '=', 'sent')])
            if not related_invoice:
                _logger.info('Error: invoice not found for receipt file: %s', attachment.fname)
                return
            related_invoice.l10n_it_send_state = 'invalid'
            error = self._return_error_xml(tree)
            related_invoice.message_post(
                body=(_("Errors in the E-Invoice :<br/>%s") % (error))
            )
            activity_vals = {
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'invoice_user_id': related_invoice.invoice_user_id.id if related_invoice.invoice_user_id else self.env.user.id
            }
            related_invoice.activity_schedule(summary='Rejection notice', **activity_vals)

        elif receipt_type == 'MC':
            # Failed delivery notice
            # This is the receipt sent by the ES to the transmitting subject if the file is not
            # delivered to the addressee.
            related_invoice = self.env['account.move'].search([
                ('l10n_it_einvoice_name', '=', filename),
                ('l10n_it_send_state', '=', 'sent')])
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
            related_invoice = self.env['account.move'].search([
                ('l10n_it_einvoice_name', '=', filename),
                ('l10n_it_send_state', '=', 'delivered')])
            if not related_invoice:
                _logger.info('Error: invoice not found for receipt file: %s', attachment.fname)
                return
            elements = tree.xpath('//Esito')
            if elements and elements[0].text:
                if elements[0].text == 'EC01':
                    related_invoice.l10n_it_send_state = 'delivered_accepted'
                elif elements[0].text == 'EC02':
                    related_invoice.l10n_it_send_state = 'delivered_refused'

            info = self._return_multi_line_xml(tree,
                                               ['//Esito',
                                                '//Descrizione',
                                                '//IdentificativoSdI',
                                                '//DataOraRicezione',
                                                '//DataOraConsegna',
                                                '//Note'
                                               ])
            related_invoice.message_post(
                body=(_("Outcome notice: %s<br/>%s") % (related_invoice.l10n_it_send_state, info))
            )
            if related_invoice.l10n_it_send_state == 'delivered_refused':
                activity_vals = {
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'invoice_user_id': related_invoice.invoice_user_id.id if related_invoice.invoice_user_id else self.env.user.id
                }
                related_invoice.activity_schedule(summary='Outcome notice: Refused', **activity_vals)

        # elif receipt_type == 'MT':
            # Metadata file
            # This is the file sent by the ES to the addressee together with the invoice file,
            # containing the main reference data of the file useful for processing, including
            # the IdentificativoSDI.
            # Useless for Odoo

        elif receipt_type == 'DT':
            # Deadline passed notice
            # This is the receipt sent by the ES to both the invoice sender and the invoice
            # addressee to communicate the expiry of the maximum term for communication of
            # acceptance/refusal.
            related_invoice = self.env['account.move'].search([
                ('l10n_it_einvoice_name', '=', filename), ('l10n_it_send_state', '=', 'delivered')])
            if not related_invoice:
                _logger.info('Error: invoice not found for receipt file: %s', attachment.fname)
                return
            related_invoice.l10n_it_send_state = 'delivered_expired'
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
            elements = tree.xpath(element_tag)
            if not elements:
                continue
            for element in elements:
                if element.text:
                    text = " ".join(element.text.split())
                    output_str += "<li>%s: %s</li>" % (element.tag, text)
        return output_str + "</ul>"

    def _return_error_xml(self, tree):
        output_str = "<ul>"

        elements = tree.xpath('//Errore')
        if not elements:
            return
        for element in elements:
            descrizione = " ".join(element[1].text.split())
            if descrizione:
                output_str += "<li>Errore %s: %s</li>" % (element[0].text, descrizione)
        return output_str + "</ul>"

class IrMailServer(models.Model):
    _name = "ir.mail_server"
    _inherit = "ir.mail_server"

    def build_email(self, email_from, email_to, subject, body, email_cc=None, email_bcc=None, reply_to=False,
                attachments=None, message_id=None, references=None, object_id=False, subtype='plain', headers=None,
                body_alternative=None, subtype_alternative='plain'):

        if self.env.context.get('wo_bounce_return_path') and headers:
            headers['Return-Path'] = email_from
        return super(IrMailServer, self).build_email(email_from, email_to, subject, body, email_cc=email_cc, email_bcc=email_bcc, reply_to=reply_to,
                attachments=attachments, message_id=message_id, references=references, object_id=object_id, subtype=subtype, headers=headers,
                body_alternative=body_alternative, subtype_alternative=subtype_alternative)
