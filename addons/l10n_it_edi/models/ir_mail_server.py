# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import zipfile
import io
import re
import logging
import email
import email.policy
import dateutil
import pytz

from lxml import etree
from datetime import datetime
from xmlrpc import client as xmlrpclib

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError
from odoo.addons.l10n_it_edi.tools.remove_signature import remove_signature


_logger = logging.getLogger(__name__)

class FetchmailServer(models.Model):
    _name = 'fetchmail.server'
    _inherit = 'fetchmail.server'

    l10n_it_is_pec = fields.Boolean('PEC server', help="If PEC Server, only mail from '...@pec.fatturapa.it' will be processed.")
    l10n_it_last_uid = fields.Integer(string='Last message UID IT', default=1)

    def _search_edi_invoice(self, att_name, send_state=False):
        """ Search sent l10n_it_edi fatturaPA invoices """

        conditions = [
            ('move_id', "!=", False),
            ('edi_format_id.code', '=', 'fattura_pa'),
            ('attachment_id.name', '=', att_name),
        ]
        if send_state:
            conditions.append(('move_id.l10n_it_send_state', '=', send_state))

        return self.env['account.edi.document'].search(conditions, limit=1).move_id

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

                # Only download new emails
                email_filter = ['(UID %s:*)' % (server.l10n_it_last_uid)]

                # The l10n_it_edi.fatturapa_bypass_incoming_address_filter prevents the sender address check on incoming email.
                bypass_incoming_address_filter = self.env['ir.config_parameter'].get_param('l10n_it_edi.bypass_incoming_address_filter', False)
                if not bypass_incoming_address_filter:
                    email_filter.append('(FROM "@pec.fatturapa.it")')

                data = imap_server.uid('search', None, *email_filter)[1]

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
                    msg_txt = email.message_from_bytes(message, policy=email.policy.SMTP)

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
        from_address = msg_txt.get('from')
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
                else:
                    att_filename = attachment.fname
                    match = re.search("([A-Z]{2}[A-Za-z0-9]{2,28}_[A-Za-z0-9]{0,5}.(xml.p7m|xml))", att_filename)
                    # If match, we have an invoice.
                    if match:
                        # If it's signed, the content has a bytes type and we just remove the signature's envelope
                        if match.groups()[1] == 'xml.p7m':
                            att_content_data = remove_signature(attachment.content)
                            # If the envelope cannot be removed, the remove_signature returns None, so we skip
                            if not att_content_data:
                                _logger.warning("E-invoice couldn't be read: %s", att_filename)
                                continue
                            att_filename = att_filename.replace('.xml.p7m', '.xml')
                        else:
                            # Otherwise, it should be an utf-8 encoded XML string
                            att_content_data = attachment.content.encode()
                    self._create_invoice_from_mail(att_content_data, att_filename, from_address)
            else:
                if split_underscore[1] == 'AT':
                    # Attestazione di avvenuta trasmissione della fattura con impossibilità di recapito
                    self._message_AT_invoice(attachment)
                else:
                    _logger.info('New E-invoice in zip file: %s', attachment.fname)
                    self._create_invoice_from_mail_with_zip(attachment, from_address)

    def _create_invoice_from_mail(self, att_content_data, att_name, from_address):
        """ Creates an invoice from the content of an email present in ir.attachments

        :param att_content_data:   The 'utf-8' encoded bytes string representing the content of the attachment.
        :param att_name:           The attachment's file name.
        :param from_address:       The sender address of the email.
        """

        invoices = self.env['account.move']

        # Check if we already imported the email as an attachment
        existing = self.env['ir.attachment'].search([('name', '=', att_name), ('res_model', '=', 'account.move')])
        if existing:
            _logger.info('E-invoice already exist: %s', att_name)
            return invoices

        # Create the new attachment for the file
        attachment = self.env['ir.attachment'].create({
            'name': att_name,
            'raw': att_content_data,
            'res_model': 'account.move',
            'type': 'binary'})

        # Decode the file.
        try:
            tree = etree.fromstring(att_content_data)
        except Exception:
            _logger.info('The xml file is badly formatted: %s', att_name)
            return invoices

        invoices = self.env.ref('l10n_it_edi.edi_fatturaPA')._create_invoice_from_xml_tree(att_name, tree)
        if not invoices:
            _logger.info('E-invoice not found in file: %s', att_name)
            return invoices
        invoices.l10n_it_send_state = "new"
        invoices.invoice_source_email = from_address
        for invoice in invoices:
            invoice.with_context(no_new_invoice=True, default_res_id=invoice.id) \
                    .message_post(body=(_("Original E-invoice XML file")), attachment_ids=[attachment.id])

        self._cr.commit()

        _logger.info('New E-invoices (%s), ids: %s', att_name, [x.id for x in invoices])
        return invoices

    def _create_invoice_from_mail_with_zip(self, attachment_zip, from_address):
        with zipfile.ZipFile(io.BytesIO(attachment_zip.content)) as z:
            for att_name in z.namelist():
                existing = self.env['ir.attachment'].search([('name', '=', att_name), ('res_model', '=', 'account.move')])
                if existing:
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

                    related_invoice = self._search_edi_invoice(filename)
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
            tree = etree.fromstring(attachment.content.encode())
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
            related_invoice = self._search_edi_invoice(filename, 'sent')
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
            related_invoice = self._search_edi_invoice(filename, 'sent')
            if not related_invoice:
                _logger.info('Error: invoice not found for receipt file: %s', attachment.fname)
                return
            related_invoice.l10n_it_send_state = 'invalid'
            error = self._return_error_xml(tree)
            related_invoice.message_post(
                body=(_("Errors in the E-Invoice :<br/>%s") % (error))
            )
            related_invoice.activity_schedule(
                'mail.mail_activity_data_todo',
                summary='Rejection notice',
                user_id=related_invoice.invoice_user_id.id if related_invoice.invoice_user_id else self.env.user.id)

        elif receipt_type == 'MC':
            # Failed delivery notice
            # This is the receipt sent by the ES to the transmitting subject if the file is not
            # delivered to the addressee.
            related_invoice = self._search_edi_invoice(filename, 'sent')
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
                file to the Administration in question again. More information:<br/>%s") % (info))
            )

        elif receipt_type == 'NE':
            # Outcome notice
            # This is the receipt sent by the ES to the invoice sender to communicate the result
            # (acceptance or refusal of the invoice) of the checks carried out on the document by
            # the addressee.
            related_invoice = self._search_edi_invoice(filename, 'delivered')
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
                related_invoice.activity_schedule(
                    'mail.mail_activity_todo',
                    user_id=related_invoice.invoice_user_id.id if related_invoice.invoice_user_id else self.env.user.id,
                    summary='Outcome notice: Refused')

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
            related_invoice = self._search_edi_invoice(filename, 'delivered')
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

    def _get_test_email_addresses(self):
        self.ensure_one()

        company = self.env["res.company"].search([("l10n_it_mail_pec_server_id", "=", self.id)], limit=1)
        if not company:
            # it's not a PEC server
            return super()._get_test_email_addresses()
        email_from = self.smtp_user
        if not email_from:
            raise UserError(_('Please configure Username for this Server PEC'))
        email_to = company.l10n_it_address_recipient_fatturapa
        if not email_to:
            raise UserError(_('Please configure Government PEC-mail	in company settings'))
        return email_from, email_to

    def build_email(self, email_from, email_to, subject, body, email_cc=None, email_bcc=None, reply_to=False,
                attachments=None, message_id=None, references=None, object_id=False, subtype='plain', headers=None,
                body_alternative=None, subtype_alternative='plain'):

        if self.env.context.get('wo_bounce_return_path') and headers:
            headers['Return-Path'] = email_from
        return super(IrMailServer, self).build_email(email_from, email_to, subject, body, email_cc=email_cc, email_bcc=email_bcc, reply_to=reply_to,
                attachments=attachments, message_id=message_id, references=references, object_id=object_id, subtype=subtype, headers=headers,
                body_alternative=body_alternative, subtype_alternative=subtype_alternative)
