# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import email
import logging
import os

from lxml import etree

from markupsafe import Markup
from xmlrpc import client as xmlrpclib

from odoo import api, fields, models, _, Command
from odoo.exceptions import ValidationError
from odoo.tools import float_compare
from odoo.tools.misc import formatLang

_logger = logging.getLogger(__name__)

XML_NAMESPACES = {
    'ns0': 'http://www.sii.cl/SiiDte',
    'ns1': 'http://www.w3.org/2000/09/xmldsig#',
    'xml_schema': 'http://www.sii.cl/XMLSchema'
}

DEFAULT_DOC_NUMBER_PADDING = 6


class FetchmailServer(models.Model):
    _name = 'fetchmail.server'
    _inherit = 'fetchmail.server'

    l10n_cl_is_dte = fields.Boolean(
        'DTE server', help='By checking this option, this email account will be used to receive the electronic\n'
                           'invoices from the suppliers, and communications from the SII regarding the electronic\n'
                           'invoices issued. In this case, this email should match both emails declared on the SII\n'
                           'site in the section: "ACTUALIZACION DE DATOS DEL CONTRIBUYENTE", "Mail Contacto SII"\n'
                           'and "Mail Contacto Empresas".')
    l10n_cl_last_uid = fields.Integer(
        string='Last read message ID (CL)', default=1,
        help='This value is pointing to the number of the last message read by odoo '
             'in the inbox. This value will be updated by the system during its normal'
             'operation.')

    @api.constrains('l10n_cl_is_dte', 'server_type')
    def _check_server_type(self):
        for record in self:
            if record.l10n_cl_is_dte and record.server_type not in ('imap', 'outlook', 'gmail'):
                raise ValidationError(_('The server must be of type IMAP.'))

    def fetch_mail(self):
        for server in self.filtered(lambda s: s.l10n_cl_is_dte):
            _logger.info('Start checking for new emails on %s IMAP server %s', server.server_type, server.name)

            # prevents the process from timing out when connecting for the first time
            # to an edi email server with too many new emails to process
            # e.g over 5k emails. We will only fetch the next 50 "new" emails
            # based on their IMAP uid
            default_batch_size = 50

            count, failed = 0, 0
            imap_server = None
            try:
                imap_server = server.connect()
                imap_server.select()

                result, data = imap_server.uid('search', None, '(UID %s:*)' % server.l10n_cl_last_uid)
                new_max_uid = server.l10n_cl_last_uid
                for uid in data[0].split()[:default_batch_size]:
                    if int(uid) <= server.l10n_cl_last_uid:
                        # We get always minimum 1 message.  If no new message, we receive the newest already managed.
                        continue

                    result, data = imap_server.uid('fetch', uid, '(RFC822)')

                    if not data[0]:
                        continue
                    message = data[0][1]

                    # To leave the mail in the state in which they were.
                    if 'Seen' not in data[1].decode('UTF-8'):
                        imap_server.uid('STORE', uid, '+FLAGS', '(\\Seen)')
                    else:
                        imap_server.uid('STORE', uid, '-FLAGS', '(\\Seen)')

                    # See details in message_process() in mail_thread.py
                    if isinstance(message, xmlrpclib.Binary):
                        message = bytes(message.data)
                    if isinstance(message, str):
                        message = message.encode('utf-8')
                    msg_txt = email.message_from_bytes(message, policy=email.policy.SMTP)
                    try:
                        server._process_incoming_email(msg_txt)
                        new_max_uid = max(new_max_uid, int(uid))
                        server.write({'l10n_cl_last_uid': new_max_uid})
                        self._cr.commit()
                    except Exception:
                        _logger.info('Failed to process mail from %s server %s.', server.server_type, server.name,
                                     exc_info=True)
                        failed += 1
                    count += 1
                server.write({'l10n_cl_last_uid': new_max_uid})
                _logger.info('Fetched %d email(s) on %s server %s; %d succeeded, %d failed.', count, server.server_type,
                             server.name, (count - failed), failed)
            except Exception:
                _logger.info('General failure when trying to fetch mail from %s server %s.', server.server_type,
                             server.name, exc_info=True)
            finally:
                if imap_server:
                    try:
                        imap_server.close()
                        imap_server.logout()
                    except Exception:  # pylint: disable=broad-except
                        _logger.warning('Failed to properly finish connection: %s.', server.name, exc_info=True)
                server.write({'date': fields.Datetime.now()})
        return super(FetchmailServer, self.filtered(lambda s: not s.l10n_cl_is_dte)).fetch_mail()

    def _process_incoming_email(self, msg_txt):
        parsed_values = self.env['mail.thread']._message_parse_extract_payload(msg_txt, {})
        body, attachments = parsed_values['body'], parsed_values['attachments']
        from_address = msg_txt.get('from')
        for attachment in attachments:
            _logger.info('Processing attachment %s' % attachment.fname)
            attachment_ext = os.path.splitext(attachment.fname)[1]
            format_content = attachment.content.encode() if isinstance(attachment.content, str) else attachment.content
            if attachment_ext.lower() != '.xml' or not self._is_dte_email(format_content):
                _logger.info('Attachment %s has been discarded! It is not a xml file or is not a DTE email' %
                             attachment.fname)
                continue
            xml_content = etree.fromstring(format_content)
            origin_type = self._get_xml_origin_type(xml_content)
            if origin_type == 'not_classified':
                _logger.info('Attachment %s has been discarded! Origin type: %s' % (attachment.fname, origin_type))
                continue
            company = self._get_dte_recipient_company(xml_content, origin_type)
            if not company or not self._is_dte_enabled_company(company):
                _logger.info('Attachment %s has been discarded! It is not a valid company (id: %s)' % (
                    attachment.fname, company.id))
                continue
            self._process_attachment_content(format_content, attachment.fname, from_address, origin_type, company.id)

    def _process_attachment_content(self, att_content, att_name, from_address, origin_type, company_id):
        """
        This could be called from a button if there is a need to be processed manually
        """
        if origin_type == 'incoming_supplier_document':
            for move in self._create_document_from_attachment(att_content, att_name, from_address, company_id):
                if move.partner_id:
                    try:
                        move._l10n_cl_send_receipt_acknowledgment()
                    except Exception as error:
                        move.message_post(body=str(error))
        elif origin_type == 'incoming_sii_dte_result':
            self._process_incoming_sii_dte_result(att_content)
        elif origin_type in ['incoming_acknowledge', 'incoming_commercial_accept', 'incoming_commercial_reject']:
            self._process_incoming_customer_claim(company_id, att_content, att_name, origin_type)

    def _process_incoming_sii_dte_result(self, att_content):
        xml_content = etree.fromstring(att_content)
        track_id = xml_content.findtext('.//TRACKID').zfill(10)
        moves = self.env['account.move'].search([('l10n_cl_sii_send_ident', '=', track_id)])
        status = xml_content.findtext('IDENTIFICACION/ESTADO')
        error_status = xml_content.findtext('REVISIONENVIO/REVISIONDTE/ESTADO')
        if error_status is not None:
            msg = _('Incoming SII DTE result:<br/> '
                    '<li><b>ESTADO</b>: %s</li>'
                    '<li><b>REVISIONDTE/ESTADO</b>: %s</li>'
                    '<li><b>REVISIONDTE/DETALLE</b>: %s</li>',
                      status, error_status, xml_content.findtext('REVISIONENVIO/REVISIONDTE/DETALLE'))
        else:
            msg = _('Incoming SII DTE result:<br/><li><b>ESTADO</b>: %s</li>', status)
        for move in moves:
            move.message_post(body=msg)

    def _process_incoming_customer_claim(self, company_id, att_content, att_name, origin_type):
        dte_tag = 'RecepcionDTE' if origin_type == 'incoming_acknowledge' else 'ResultadoDTE'
        xml_content = etree.fromstring(att_content)
        for dte in xml_content.xpath('//ns0:%s' % dte_tag, namespaces=XML_NAMESPACES):
            document_number = self._get_document_number(dte)
            issuer_vat = self._get_dte_receptor_vat(dte)
            partner = self._get_partner(issuer_vat, company_id)
            if not partner:
                _logger.warning('Partner for incoming customer claim has not been found for %s', issuer_vat)
                continue
            document_type_code = self._get_document_type_from_xml(dte)
            document_type = self.env['l10n_latam.document.type'].search(
                [('code', '=', document_type_code), ('country_id.code', '=', 'CL')], limit=1)
            move = self.env['account.move'].sudo().search([
                ('partner_id', '=', partner.id),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('l10n_latam_document_type_id', '=', document_type.id),
                ('l10n_cl_dte_status', '=', 'accepted'),
                ('name', '=ilike', f'{document_type.doc_code_prefix}%{document_number}'),
                ('company_id', '=', company_id),
            ]).filtered(lambda m: m.name.split()[1].lstrip('0') == document_number)

            if not move:
                _logger.warning('Move not found with partner: %s, document_number: %s, l10n_latam_document_type: %s, '
                              'company_id: %s', partner.id, document_number, document_type.id, company_id)
                continue

            if len(move) > 1:
                _logger.warning('Multiple moves found for partner: %s, document_number: %s, l10n_latam_document_type: %s, '
                            'company_id: %s. Expected only one move.', partner.id, document_number, document_type.id, company_id)
                continue

            status = {'incoming_acknowledge': 'received', 'incoming_commercial_accept': 'accepted'}.get(
                origin_type, 'claimed')
            move.write({'l10n_cl_dte_acceptation_status': status})
            move.with_context(no_new_invoice=True).message_post(
                body=_('DTE reception status established as <b>%s</b> by incoming email', status),
                attachments=[(att_name, att_content)])

    def _check_document_number_exists(self, partner_id, document_number, document_type, company_id):
        to_check_documents = self.env['account.move'].sudo().search(
            [('move_type', 'in', ['in_invoice', 'in_refund']),
             ('name', 'ilike', document_number),
             ('partner_id', '=', partner_id),
             ('company_id', '=', company_id)])

        return len(to_check_documents.filtered(
            lambda x: x.l10n_latam_document_type_id.code == document_type.code and
                      x.l10n_latam_document_number.lstrip('0') == document_number.lstrip('0')
        )) > 0

    def _check_document_number_exists_no_partner(self, document_number, document_type, company_id, vat):
        """ This is a separate method for the no partner case to not modify the other method in stable.
            If the partner is not found, we put its vat in the narration field, so we avoid to import twice.
        """
        to_check_documents = self.env['account.move'].sudo().search([
            ('move_type', 'in', ['in_invoice', 'in_refund']),
            ('name', 'ilike', document_number),
            ('partner_id', '=', False),
            ('narration', '=', vat),
            ('company_id', '=', company_id)])

        return len(to_check_documents.filtered(
            lambda x: x.l10n_latam_document_type_id.code == document_type.code and
                      x.l10n_latam_document_number.lstrip('0') == document_number.lstrip('0')
        )) > 0

    def _create_document_from_attachment(self, att_content, att_name, from_address, company_id):
        moves = []
        xml_content = etree.fromstring(att_content)
        for dte_xml in xml_content.xpath('//ns0:DTE', namespaces=XML_NAMESPACES):
            document_number = self._get_document_number(dte_xml)
            document_type_code = self._get_document_type_from_xml(dte_xml)
            xml_total_amount = float(dte_xml.findtext('.//ns0:MntTotal', namespaces=XML_NAMESPACES))
            document_type = self.env['l10n_latam.document.type'].search(
                [('code', '=', document_type_code), ('country_id.code', '=', 'CL')], limit=1)
            if not document_type:
                _logger.info('DTE has been discarded! Document type %s not found' % document_type_code)
                continue
            if document_type and document_type.internal_type not in ['invoice', 'debit_note', 'credit_note']:
                _logger.info('DTE has been discarded! The document type %s is not a vendor bill' % document_type_code)
                continue

            issuer_vat = self._get_dte_issuer_vat(dte_xml)
            partner = self._get_partner(issuer_vat, company_id)
            if partner and self._check_document_number_exists(partner.id, document_number, document_type, company_id) \
                    or (not partner and self._check_document_number_exists_no_partner(document_number, document_type,
                                                                                      company_id, issuer_vat)):
                _logger.info('E-invoice already exist: %s', document_number)
                continue

            default_move_type = 'in_invoice' if document_type_code != '61' else 'in_refund'
            msgs = []
            try:
                invoice_form, msgs = self._get_invoice_form(
                    company_id, partner, default_move_type, from_address, dte_xml, document_number, document_type, msgs)

            except Exception as error:
                _logger.info(error)
                with self.env.cr.savepoint(), self.env['account.move'].with_context(
                        default_move_type=default_move_type, allowed_company_ids=[company_id])._get_edi_creation() as invoice_form:
                    msgs.append(str(error))
                    invoice_form.partner_id = partner
                    invoice_form.l10n_latam_document_type_id = document_type
                    invoice_form.l10n_latam_document_number = document_number

            if not partner:
                invoice_form.narration = issuer_vat or ''
            move = invoice_form

            dte_attachment = self.env['ir.attachment'].create({
                'name': 'DTE_{}.xml'.format(document_number),
                'res_model': move._name,
                'res_id': move.id,
                'type': 'binary',
                'datas': base64.b64encode(etree.tostring(dte_xml))
            })
            move.l10n_cl_dte_file = dte_attachment.id

            for msg in msgs:
                move.with_context(no_new_invoice=True).message_post(body=msg)

            msg = _('Vendor Bill DTE has been generated for the following vendor:') if partner else \
                  _('Vendor not found: You can generate this vendor manually with the following information:')
            msg += Markup('<br/>')
            move.with_context(no_new_invoice=True).message_post(
                body=msg + Markup(_(
                    '<li><b>Name</b>: %(name)s</li><li><b>RUT</b>: %(vat)s</li><li>'
                    '<b>Address</b>: %(address)s</li>')) % {
                    'vat': self._get_dte_issuer_vat(xml_content) or '',
                    'name': self._get_dte_partner_name(xml_content) or '',
                    'address': self._get_dte_issuer_address(xml_content) or ''}, attachment_ids=[dte_attachment.id])

            if float_compare(move.amount_total, xml_total_amount, precision_digits=move.currency_id.decimal_places) != 0:
                move.message_post(
                    body=Markup(_('<strong>Warning:</strong> The total amount of the DTE\'s XML is %s and the total amount '
                           'calculated by Odoo is %s. Typically this is caused by additional lines in the detail or '
                           'by unidentified taxes, please check if a manual correction is needed.'))
                    % (formatLang(self.env, xml_total_amount, currency_obj=move.currency_id),
                       formatLang(self.env, move.amount_total, currency_obj=move.currency_id)))
            move.l10n_cl_dte_acceptation_status = 'received'
            moves.append(move)
            _logger.info('New move has been created from DTE %s with id: %s', att_name, move.id)
        return moves

    def _get_invoice_form(self, company_id, partner, default_move_type, from_address, dte_xml, document_number,
                          document_type, msgs):
        """
        This method creates a draft vendor bill from the attached xml in the incoming email.
        """
        with self.env.cr.savepoint(), self.env['account.move'].with_context(
                default_invoice_source_email=from_address,
                default_move_type=default_move_type, allowed_company_ids=[company_id])._get_edi_creation() as invoice_form:
            journal = self._get_dte_purchase_journal(company_id)
            if journal:
                invoice_form.journal_id = journal

            invoice_form.partner_id = partner
            invoice_date = dte_xml.findtext('.//ns0:FchEmis', namespaces=XML_NAMESPACES)
            if invoice_date is not None:
                invoice_form.invoice_date = fields.Date.from_string(invoice_date)
            # Set the date after invoice_date to avoid the onchange
            invoice_form.date = fields.Date.context_today(
                self.with_context(tz='America/Santiago'))

            invoice_date_due = dte_xml.findtext('.//ns0:FchVenc', namespaces=XML_NAMESPACES)
            if invoice_date_due is not None:
                invoice_form.invoice_date_due = fields.Date.from_string(invoice_date_due)

            currency = self._get_dte_currency(dte_xml)
            if currency:
                invoice_form.currency_id = currency

            invoice_form.l10n_latam_document_type_id = document_type
            invoice_form.l10n_latam_document_number = document_number
            dte_lines = self._get_dte_lines(dte_xml, company_id, partner.id)
            invoice_form.write({
                'invoice_line_ids': [
                    Command.create({
                        'product_id': dte_line.get('product', self.env['product.product']).id,
                        'name': dte_line.get('name'),
                        'quantity': dte_line.get('quantity'),
                        'price_unit': dte_line.get('price_unit'),
                        'discount': dte_line.get('discount', 0),
                        'tax_ids': [Command.set([tax.id for tax in dte_line.get('taxes', [])])],
                    })
                    for dte_line in dte_lines
                ],
                'l10n_cl_reference_ids': [
                    Command.create({
                        'origin_doc_number': reference_line['origin_doc_number'],
                        'reference_doc_code': reference_line['reference_doc_code'],
                        'l10n_cl_reference_doc_type_id': reference_line['l10n_cl_reference_doc_type_id'].id,
                        'reason': reference_line['reason'],
                        'date': reference_line['date'],
                    })
                    for reference_line in self._get_invoice_references(dte_xml)
                ],
            })
            for line, dte_line in zip(invoice_form.invoice_line_ids, dte_lines):
                if dte_line.get('default_tax'):
                    default_tax = line._get_computed_taxes()
                    if default_tax not in line.tax_ids:
                        line.tax_ids += default_tax
        return invoice_form, msgs

    def _is_dte_email(self, attachment_content):
        return b'http://www.sii.cl/SiiDte' in attachment_content or b'<RESULTADO_ENVIO>' in attachment_content

    def _get_dte_recipient_company(self, xml_content, origin_type):
        xml_tag_by_type = {
            'incoming_supplier_document': '//ns0:RutReceptor',
            'incoming_sii_dte_result': '//RUTEMISOR',
            'incoming_acknowledge': '//ns0:RutRecibe',
            'incoming_commercial_accept': '//ns0:RutRecibe',
            'incoming_commercial_reject': '//ns0:RutRecibe',
        }
        receiver_rut = xml_content.xpath(
            xml_tag_by_type.get(origin_type), namespaces=XML_NAMESPACES)
        if not receiver_rut:
            return None
        return self.env['res.company'].sudo().search([('vat', '=', receiver_rut[0].text)])

    def _is_dte_enabled_company(self, company):
        return False if not company.l10n_cl_dte_service_provider else True

    def _get_xml_origin_type(self, xml_content):
        tag = etree.QName(xml_content.tag).localname
        if tag == 'EnvioDTE':
            return 'incoming_supplier_document'
        if tag == 'RespuestaDTE':
            if xml_content.findtext('.//ns0:EstadoRecepDTE', namespaces=XML_NAMESPACES) == '0':
                return 'incoming_acknowledge'
            if xml_content.findtext('.//ns0:EstadoDTE', namespaces=XML_NAMESPACES) == '0':
                return 'incoming_commercial_accept'
            return 'incoming_commercial_reject'
        if tag == 'RESULTADO_ENVIO':
            return 'incoming_sii_dte_result'
        return 'not_classified'

    def _get_partner(self, partner_rut, company_id):
        return self.env["res.partner"].search(
            [
                ("vat", "=", partner_rut),
                "|",
                ("company_id", "=", company_id),
                ("company_id", "=", False),
            ],
            limit=1,
        )

    def _get_dte_issuer_vat(self, xml_content):
        return (xml_content.findtext('.//ns0:RUTEmisor', namespaces=XML_NAMESPACES).upper() or
                xml_content.findtext('.//ns0:RutEmisor', namespaces=XML_NAMESPACES).upper())

    def _get_dte_receptor_vat(self, xml_content):
        return (xml_content.findtext('.//ns0:RUTRecep', namespaces=XML_NAMESPACES).upper() or
                xml_content.findtext('.//ns0:RutReceptor', namespaces=XML_NAMESPACES).upper())

    def _get_dte_partner_name(self, xml_content):
        return xml_content.findtext('.//ns0:RznSoc', namespaces=XML_NAMESPACES)

    def _get_dte_issuer_address(self, xml_content):
        return xml_content.findtext('.//ns0:DirOrigen', default='', namespaces=XML_NAMESPACES)

    def _get_dte_purchase_journal(self, company_id):
        return self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(company_id),
            ('type', '=', 'purchase'),
            ('l10n_latam_use_documents', '=', True),
        ], limit=1)

    def _get_document_number(self, xml_content):
        return xml_content.findtext('.//ns0:Folio', namespaces=XML_NAMESPACES)

    def _get_document_type_from_xml(self, xml_content):
        return xml_content.findtext('.//ns0:TipoDTE', namespaces=XML_NAMESPACES)

    def _get_doc_number_padding(self, company_id):
        """Returns the document number padding used to create the name of the account move"""
        move = self.env['account.move'].sudo().search([
            ('company_id', '=', company_id),
            ('name', 'not in', (False, '/', ''))
        ], order='create_date desc', limit=1)
        if not move:
            return DEFAULT_DOC_NUMBER_PADDING
        doc_number = move.name.split(' ')[1]
        return len(doc_number)

    def _use_default_tax(self, dte_xml):
        """We use the default tax if the DTE has the tag TasaIVA"""
        return dte_xml.findtext('.//ns0:TasaIVA', namespaces=XML_NAMESPACES) is not None

    def _get_withholding_taxes(self, company_id, dte_line):
        # Get withholding taxes from DTE line
        tax_codes = [int(element.text) for element in dte_line.findall('.//ns0:CodImpAdic', namespaces=XML_NAMESPACES)]
        return set(self.env['account.tax'].search([
            *self.env['account.tax']._check_company_domain(company_id),
            ('type_tax_use', '=', 'purchase'),
            ('l10n_cl_sii_code', 'in', tax_codes)
        ]))

    def _get_dte_currency(self, dte_xml):
        currency_name = dte_xml.findtext('.//ns0:Moneda', namespaces=XML_NAMESPACES)
        if currency_name is None:  # If the currency of the DTE is CLP then the tag doesn't exist
            currency_name = 'CLP'
        return self.env['res.currency'].with_context(active_test=False).search([('name', '=', currency_name)])

    def _get_vendor_product(self, product_code, product_name, company_id, partner_id):
        """
        This tries to match products specified in the vendor bill with current products in database.
        Criteria to attempt a match with existent products:
        1) check if product_code in the supplier info is present (if partner_id is established)
        2) if (1) fails, check if product supplier info name is present (if partner_id is established)
        3) if (1) and (2) fail, check product default_code
        4) if 3 previous criteria fail, check product name, and return false if fails
        """
        if partner_id:
            supplier_info_domain = [
                *self.env['product.supplierinfo']._check_company_domain(company_id),
                ('partner_id', '=', partner_id),
            ]
            if product_code:
                # 1st criteria
                supplier_info_domain.append(('product_code', '=', product_code))
            else:
                # 2nd criteria
                supplier_info_domain.append(('product_name', '=', product_name))
            supplier_info = self.env['product.supplierinfo'].sudo().search(supplier_info_domain, limit=1)
            if supplier_info:
                return supplier_info.product_id
        # 3rd criteria
        if product_code:
            product = self.env['product.product'].sudo().search([
                *self.env['product.product']._check_company_domain(company_id),
                '|', ('default_code', '=', product_code), ('barcode', '=', product_code),
            ], limit=1)
            if product:
                return product
        # 4th criteria
        return self.env['product.product'].sudo().search([
            *self.env['product.product']._check_company_domain(company_id),
            ('name', 'ilike', product_name),
        ], limit=1)

    def _get_dte_lines(self, dte_xml, company_id, partner_id):
        """
        This parse DTE invoice detail lines and tries to match lines with existing products.
        If no products are found, it puts only the description of the products in the draft invoice lines
        """
        gross_amount = dte_xml.findtext('.//ns0:MntBruto', namespaces=XML_NAMESPACES) is not None
        default_purchase_tax = self.env['account.tax'].search([
            *self.env['account.tax']._check_company_domain(company_id),
            ('l10n_cl_sii_code', '=', 14),
            ('type_tax_use', '=', 'purchase'),
        ], limit=1)
        currency = self._get_dte_currency(dte_xml)
        invoice_lines = []
        for dte_line in dte_xml.findall('.//ns0:Detalle', namespaces=XML_NAMESPACES):
            product_code = dte_line.findtext('.//ns0:VlrCodigo', namespaces=XML_NAMESPACES)
            product_name = dte_line.findtext('.//ns0:NmbItem', namespaces=XML_NAMESPACES)
            product = self._get_vendor_product(product_code, product_name, company_id, partner_id)
            # the QtyItem tag is not mandatory in certain cases (case 2 in documentation).
            # Should be set to 1 if not present.
            # See http://www.sii.cl/factura_electronica/formato_dte.pdf row 15 and row 22 of tag table
            quantity = float(dte_line.findtext('.//ns0:QtyItem', default=1, namespaces=XML_NAMESPACES))
            # in the same case, PrcItem is not mandatory if QtyItem is not present, but MontoItem IS mandatory
            # this happens whenever QtyItem is not present in the invoice.
            # See http://www.sii.cl/factura_electronica/formato_dte.pdf row 38 of tag table.
            price_unit = float(dte_line.findtext(
                './/ns0:PrcItem', default=dte_line.findtext('.//ns0:MontoItem', namespaces=XML_NAMESPACES),
                namespaces=XML_NAMESPACES))
            discount = float(dte_line.findtext('.//ns0:DescuentoPct', default=0, namespaces=XML_NAMESPACES))\
                       or (float(dte_line.findtext('.//ns0:DescuentoMonto', default=0, namespaces=XML_NAMESPACES)) / (price_unit * quantity) * 100
                           if price_unit * quantity != 0 else 0)
            values = {
                'product': product,
                'name': product.name if product else dte_line.findtext('.//ns0:NmbItem', namespaces=XML_NAMESPACES),
                'quantity': quantity,
                'price_unit': price_unit,
                'discount': discount,
                'default_tax': False
            }
            if (dte_xml.findtext('.//ns0:TasaIVA', namespaces=XML_NAMESPACES) is not None and
                    dte_line.findtext('.//ns0:IndExe', namespaces=XML_NAMESPACES) is None):
                values['default_tax'] = True
                values['taxes'] = set(default_purchase_tax) | self._get_withholding_taxes(company_id, dte_line)
            if gross_amount:
                # in case the tag MntBruto is included in the IdDoc section, and there are not
                # additional taxes (withholdings)
                # even if the company has not selected its default tax value, we deduct it
                # from the price unit, gathering the value rate of the l10n_cl default purchase tax
                values['price_unit'] = default_purchase_tax.with_context(
                 force_price_include=True).compute_all(price_unit, currency)['total_excluded']
            invoice_lines.append(values)

        for desc_rcg_global in dte_xml.findall('.//ns0:DscRcgGlobal', namespaces=XML_NAMESPACES):
            line_type = desc_rcg_global.findtext('.//ns0:TpoMov', namespaces=XML_NAMESPACES)
            price_type = desc_rcg_global.findtext('.//ns0:TpoValor', namespaces=XML_NAMESPACES)
            valor_dr = (desc_rcg_global.findtext('.//ns0:ValorDROtrMnda', namespaces=XML_NAMESPACES) or
                        desc_rcg_global.findtext('.//ns0:ValorDR', namespaces=XML_NAMESPACES))
            values = {
                'name': 'DESCUENTO' if line_type == 'D' else 'RECARGO',
                'quantity': 1,
            }
            amount_dr = float(valor_dr)
            percent_dr = amount_dr / 100
            # The price unit of a discount line should be negative while surcharge should be positive
            price_unit_multiplier = 1 if line_type == 'D' else -1
            if price_type == '%':
                inde_exe_dr = desc_rcg_global.findtext('.//ns0:IndExeDR', namespaces=XML_NAMESPACES)
                if inde_exe_dr is None:  # Applied to items with tax
                    dte_amount_tag = (dte_xml.findtext('.//ns0:MntNetoOtrMnda', namespaces=XML_NAMESPACES) or
                                      dte_xml.findtext('.//ns0:MntNeto', namespaces=XML_NAMESPACES))
                    dte_amount = int(dte_amount_tag or 0)
                    # as MntNeto value is calculated after discount
                    # we need to calculate back the amount before discount in order to apply the percentage
                    # and know the amount of the discount.
                    dte_amount_before_discount = dte_amount / (1 - percent_dr)
                    values['price_unit'] = - price_unit_multiplier * dte_amount_before_discount * percent_dr
                    values['default_tax'] = self._use_default_tax(dte_xml)
                elif inde_exe_dr == '2':  # Applied to items not billable
                    dte_amount_tag = dte_xml.findtext('.//ns0:MontoNF', namespaces=XML_NAMESPACES)
                    dte_amount = dte_amount_tag is not None and int(dte_amount_tag) or 0
                    values['price_unit'] = round(
                        dte_amount - (int(dte_amount) / (1 - amount_dr / 100))) * price_unit_multiplier
                elif inde_exe_dr == '1':  # Applied to items without taxes
                    dte_amount_tag = (dte_xml.findtext('.//ns0:MntExeOtrMnda', namespaces=XML_NAMESPACES) or
                                      dte_xml.findtext('.//ns0:MntExe', namespaces=XML_NAMESPACES))
                    dte_amount = dte_amount_tag is not None and int(dte_amount_tag) or 0
                    values['price_unit'] = round(
                        dte_amount - (int(dte_amount) / (1 - amount_dr / 100))) * price_unit_multiplier
            else:
                if gross_amount:
                    amount_dr = default_purchase_tax.with_context(force_price_include=True).compute_all(
                        amount_dr, currency)['total_excluded']
                values['price_unit'] = amount_dr * -1 * price_unit_multiplier
                if desc_rcg_global.findtext('.//ns0:IndExeDR', namespaces=XML_NAMESPACES) not in ['1', '2']:
                    values['default_tax'] = self._use_default_tax(dte_xml)
            invoice_lines.append(values)
        return invoice_lines

    def _get_invoice_references(self, dte_xml):
        invoice_reference_ids = []
        for reference in dte_xml.findall('.//ns0:Referencia', namespaces=XML_NAMESPACES):
            new_reference = {
                'reference_doc_type': reference.findtext('.//ns0:TpoDocRef', namespaces=XML_NAMESPACES),
                'origin_doc_number': reference.findtext('.//ns0:FolioRef', namespaces=XML_NAMESPACES),
                'reference_doc_code': reference.findtext('.//ns0:CodRef', namespaces=XML_NAMESPACES),
                'reason': reference.findtext('.//ns0:RazonRef', namespaces=XML_NAMESPACES),
                'date': reference.findtext('.//ns0:FchRef', namespaces=XML_NAMESPACES),
            }
            new_reference['l10n_cl_reference_doc_type_id'] = self.env['l10n_latam.document.type'].search(
                [('code', '=', new_reference['reference_doc_type'])], limit=1)
            if not new_reference['l10n_cl_reference_doc_type_id']:
                new_reference['reason'] = '%s: %s' % (new_reference['reference_doc_type'], new_reference['reason'])
            invoice_reference_ids.append(new_reference)
        return invoice_reference_ids
