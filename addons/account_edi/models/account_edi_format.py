# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.tools.pdf import OdooPdfFileReader
from odoo.osv import expression
from odoo.tools import html_escape
from odoo.exceptions import RedirectWarning

from lxml import etree
import base64
import io
import logging
import pathlib
import re

_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _name = 'account.edi.format'
    _description = 'EDI format'

    name = fields.Char()
    code = fields.Char(required=True)

    _sql_constraints = [
        ('unique_code', 'unique (code)', 'This code already exists')
    ]


    ####################################################
    # Low-level methods
    ####################################################

    @api.model_create_multi
    def create(self, vals_list):
        edi_formats = super().create(vals_list)

        # activate by default on journal
        journals = self.env['account.journal'].search([])
        journals._compute_edi_format_ids()

        # activate cron
        if any(edi_format._needs_web_services() for edi_format in edi_formats):
            self.env.ref('account_edi.ir_cron_edi_network').active = True

        return edi_formats

    ####################################################
    # Export method to override based on EDI Format
    ####################################################

    def _get_invoice_edi_content(self, move):
        ''' Create a bytes literal of the file content representing the invoice - to be overridden by the EDI Format
        :returns:       bytes literal of the content generated (typically XML).
        '''
        return b''

    def _get_payment_edi_content(self, move):
        ''' Create a bytes literal of the file content representing the payment - to be overridden by the EDI Format
        :returns:       bytes literal of the content generated (typically XML).
        '''
        return b''

    def _is_required_for_invoice(self, invoice):
        """ Indicate if this EDI must be generated for the invoice passed as parameter.

        :param invoice: An account.move having the invoice type.
        :returns:       True if the EDI must be generated, False otherwise.
        """
        # TO OVERRIDE
        self.ensure_one()
        return True

    def _is_required_for_payment(self, payment):
        """ Indicate if this EDI must be generated for the payment passed as parameter.

        :param payment: An account.move linked to either an account.payment, either an account.bank.statement.line.
        :returns:       True if the EDI must be generated, False otherwise.
        """
        # TO OVERRIDE
        self.ensure_one()
        return False

    def _needs_web_services(self):
        """ Indicate if the EDI must be generated asynchronously through to some web services.

        :return: True if such a web service is available, False otherwise.
        """
        self.ensure_one()
        return False

    def _is_compatible_with_journal(self, journal):
        """ Indicate if the EDI format should appear on the journal passed as parameter to be selected by the user.
        If True, this EDI format will appear on the journal.

        :param journal: The journal.
        :returns:       True if this format can appear on the journal, False otherwise.
        """
        # TO OVERRIDE
        self.ensure_one()
        return journal.type == 'sale'

    def _is_enabled_by_default_on_journal(self, journal):
        """ Indicate if the EDI format should be selected by default on the journal passed as parameter.
        If True, this EDI format will be selected by default on the journal.

        :param journal: The journal.
        :returns:       True if this format should be enabled by default on the journal, False otherwise.
        """
        return True

    def _support_batching(self, move, state, company):
        """ Indicate if we can send multiple documents in the same time to the web services.
        If True, the _post_%s_edi methods will get multiple documents in the same time.
        Otherwise, these methods will be called with only one record at a time.

        :param move:    The move that we are trying to batch.
        :param state:   The EDI state of the move.
        :param company: The company with which we are sending the EDI.
        :returns:       True if batching is supported, False otherwise.
        """
        # TO OVERRIDE
        return False

    def _get_batch_key(self, move, state):
        """ Returns a tuple that will be used as key to partitionnate the invoices/payments when creating batches
        with multiple invoices/payments.
        The type of move (invoice or payment), its company_id, its edi state and the edi_format are used by default, if
        no further partition is needed for this format, this method should return (). It's not necessary to repeat those
        fields in the custom key.

        :param move:    The move to batch.
        :param state:   The EDI state of the move.
        :returns: The key to be used when partitionning the batches.
        """
        move.ensure_one()
        return ()

    def _check_move_configuration(self, move):
        """ Checks the move and relevant records for potential error (missing data, etc).

        :param move:    The move to check.
        :returns:       A list of error messages.
        """
        # TO OVERRIDE
        return []

    def _post_invoice_edi(self, invoices):
        """ Create the file content representing the invoice (and calls web services if necessary).

        :param invoices:    A list of invoices to post.
        :returns:           A dictionary with the invoice as key and as value, another dictionary:
        * success:          True if the edi was successfully posted.
        * attachment:       The attachment representing the invoice in this edi_format.
        * error:            An error if the edi was not successfully posted.
        * blocking_level:   (optional) How bad is the error (how should the edi flow be blocked ?)
        """
        # TO OVERRIDE
        self.ensure_one()
        return {}

    def _cancel_invoice_edi(self, invoices):
        """Calls the web services to cancel the invoice of this document.

        :param invoices:    A list of invoices to cancel.
        :returns:           A dictionary with the invoice as key and as value, another dictionary:
        * success:          True if the invoice was successfully cancelled.
        * error:            An error if the edi was not successfully cancelled.
        * blocking_level:   (optional) How bad is the error (how should the edi flow be blocked ?)
        """
        # TO OVERRIDE
        self.ensure_one()
        return {invoice: {'success': True} for invoice in invoices}  # By default, cancel succeeds doing nothing.

    def _post_payment_edi(self, payments):
        """ Create the file content representing the payment (and calls web services if necessary).

        :param payments:   The payments to post.
        :returns:           A dictionary with the payment as key and as value, another dictionary:
        * attachment:       The attachment representing the payment in this edi_format if the edi was successfully posted.
        * error:            An error if the edi was not successfully posted.
        * blocking_level:   (optional) How bad is the error (how should the edi flow be blocked ?)
        """
        # TO OVERRIDE
        self.ensure_one()
        return {}

    def _cancel_payment_edi(self, payments):
        """Calls the web services to cancel the payment of this document.

        :param payments:  A list of payments to cancel.
        :returns:         A dictionary with the payment as key and as value, another dictionary:
        * success:        True if the payment was successfully cancelled.
        * error:          An error if the edi was not successfully cancelled.
        * blocking_level: (optional) How bad is the error (how should the edi flow be blocked ?)
        """
        # TO OVERRIDE
        self.ensure_one()
        return {payment: {'success': True} for payment in payments}  # By default, cancel succeeds doing nothing.

    ####################################################
    # Import methods to override based on EDI Format
    ####################################################

    def _create_invoice_from_xml_tree(self, filename, tree, journal=None):
        """ Create a new invoice with the data inside the xml.

        :param filename: The name of the xml.
        :param tree:     The tree of the xml to import.
        :param journal:  The journal on which importing the invoice.
        :returns:        The created invoice.
        """
        # TO OVERRIDE
        self.ensure_one()
        return self.env['account.move']

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        """ Update an existing invoice with the data inside the xml.

        :param filename: The name of the xml.
        :param tree:     The tree of the xml to import.
        :param invoice:  The invoice to update.
        :returns:        The updated invoice.
        """
        # TO OVERRIDE
        self.ensure_one()
        return self.env['account.move']

    def _create_invoice_from_pdf_reader(self, filename, reader):
        """ Create a new invoice with the data inside a pdf.

        :param filename: The name of the pdf.
        :param reader:   The OdooPdfFileReader of the pdf to import.
        :returns:        The created invoice.
        """
        # TO OVERRIDE
        self.ensure_one()

        return self.env['account.move']

    def _update_invoice_from_pdf_reader(self, filename, reader, invoice):
        """ Update an existing invoice with the data inside the pdf.

        :param filename: The name of the pdf.
        :param reader:   The OdooPdfFileReader of the pdf to import.
        :param invoice:  The invoice to update.
        :returns:        The updated invoice.
        """
        # TO OVERRIDE
        self.ensure_one()
        return self.env['account.move']

    def _create_invoice_from_binary(self, filename, content, extension):
        """ Create a new invoice with the data inside a binary file.

        :param filename:  The name of the file.
        :param content:   The content of the binary file.
        :param extension: The extensions as a string.
        :returns:         The created invoice.
        """
        # TO OVERRIDE
        self.ensure_one()
        return self.env['account.move']

    def _update_invoice_from_binary(self, filename, content, extension, invoice):
        """ Update an existing invoice with the data inside a binary file.

        :param filename: The name of the file.
        :param content:  The content of the binary file.
        :param extension: The extensions as a string.
        :param invoice:  The invoice to update.
        :returns:        The updated invoice.
        """
        # TO OVERRIDE
        self.ensure_one()
        return self.env['account.move']

    def _prepare_invoice_report(self, pdf_writer, edi_document):
        """
        Prepare invoice report to be printed.
        :param pdf_writer: The pdf writer with the invoice pdf content loaded.
        :param edi_document: The edi document to be added to the pdf file.
        """
        # TO OVERRIDE
        self.ensure_one()

    ####################################################
    # Import Internal methods (not meant to be overridden)
    ####################################################

    def _decode_xml(self, filename, content):
        """Decodes an xml into a list of one dictionary representing an attachment.

        :param filename:    The name of the xml.
        :param content:     The bytes representing the xml.
        :returns:           A list with a dictionary.
        * filename:         The name of the attachment.
        * content:          The content of the attachment.
        * type:             The type of the attachment.
        * xml_tree:         The tree of the xml if type is xml.
        """
        to_process = []
        try:
            xml_tree = etree.fromstring(content)
        except Exception as e:
            _logger.exception("Error when converting the xml content to etree: %s" % e)
            return to_process
        if len(xml_tree):
            to_process.append({
                'filename': filename,
                'content': content,
                'type': 'xml',
                'xml_tree': xml_tree,
            })
        return to_process

    def _decode_pdf(self, filename, content):
        """Decodes a pdf and unwrap sub-attachment into a list of dictionary each representing an attachment.

        :param filename:    The name of the pdf.
        :param content:     The bytes representing the pdf.
        :returns:           A list of dictionary for each attachment.
        * filename:         The name of the attachment.
        * content:          The content of the attachment.
        * type:             The type of the attachment.
        * xml_tree:         The tree of the xml if type is xml.
        * pdf_reader:       The pdf_reader if type is pdf.
        """
        to_process = []
        try:
            buffer = io.BytesIO(content)
            pdf_reader = OdooPdfFileReader(buffer, strict=False)
        except Exception as e:
            # Malformed pdf
            _logger.exception("Error when reading the pdf: %s" % e)
            return to_process

        # Process embedded files.
        try:
            for xml_name, content in pdf_reader.getAttachments():
                to_process.extend(self._decode_xml(xml_name, content))
        except NotImplementedError as e:
            _logger.warning("Unable to access the attachments of %s. Tried to decrypt it, but %s." % (filename, e))

        # Process the pdf itself.
        to_process.append({
            'filename': filename,
            'content': content,
            'type': 'pdf',
            'pdf_reader': pdf_reader,
        })

        return to_process

    def _decode_binary(self, filename, content):
        """Decodes any file into a list of one dictionary representing an attachment.
        This is a fallback for all files that are not decoded by other methods.

        :param filename:    The name of the file.
        :param content:     The bytes representing the file.
        :returns:           A list with a dictionary.
        * filename:         The name of the attachment.
        * content:          The content of the attachment.
        * type:             The type of the attachment.
        """
        return [{
            'filename': filename,
            'extension': ''.join(pathlib.Path(filename).suffixes),
            'content': content,
            'type': 'binary',
        }]

    def _decode_attachment(self, attachment):
        """Decodes an ir.attachment and unwrap sub-attachment into a list of dictionary each representing an attachment.

        :param attachment:  An ir.attachment record.
        :returns:           A list of dictionary for each attachment.
        * filename:         The name of the attachment.
        * content:          The content of the attachment.
        * type:             The type of the attachment.
        * xml_tree:         The tree of the xml if type is xml.
        * pdf_reader:       The pdf_reader if type is pdf.
        """
        content = base64.b64decode(attachment.with_context(bin_size=False).datas)
        to_process = []

        # XML attachments received by mail have a 'text/plain' mimetype.
        # Therefore, if content start with '<?xml', it is considered as XML.
        is_text_plain_xml = 'text/plain' in attachment.mimetype and content.startswith(b'<?xml')
        if 'pdf' in attachment.mimetype:
            to_process.extend(self._decode_pdf(attachment.name, content))
        elif 'xml' in attachment.mimetype or is_text_plain_xml:
            to_process.extend(self._decode_xml(attachment.name, content))
        else:
            to_process.extend(self._decode_binary(attachment.name, content))

        return to_process

    def _create_invoice_from_attachment(self, attachment):
        """Decodes an ir.attachment to create an invoice.

        :param attachment:  An ir.attachment record.
        :returns:           The invoice where to import data.
        """
        for file_data in self._decode_attachment(attachment):
            for edi_format in self:
                res = False
                try:
                    if file_data['type'] == 'xml':
                        res = edi_format.with_company(self.env.company)._create_invoice_from_xml_tree(file_data['filename'], file_data['xml_tree'])
                    elif file_data['type'] == 'pdf':
                        res = edi_format.with_company(self.env.company)._create_invoice_from_pdf_reader(file_data['filename'], file_data['pdf_reader'])
                        file_data['pdf_reader'].stream.close()
                    else:
                        res = edi_format._create_invoice_from_binary(file_data['filename'], file_data['content'], file_data['extension'])
                except RedirectWarning as rw:
                    raise rw
                except Exception as e:
                    _logger.exception("Error importing attachment \"%s\" as invoice with format \"%s\"", file_data['filename'], edi_format.name, str(e))
                if res:
                    return res
        return self.env['account.move']

    def _update_invoice_from_attachment(self, attachment, invoice):
        """Decodes an ir.attachment to update an invoice.

        :param attachment:  An ir.attachment record.
        :returns:           The invoice where to import data.
        """
        for file_data in self._decode_attachment(attachment):
            for edi_format in self:
                res = False
                try:
                    if file_data['type'] == 'xml':
                        res = edi_format.with_context(default_move_type=invoice.move_type).with_company(invoice.company_id)._update_invoice_from_xml_tree(file_data['filename'], file_data['xml_tree'], invoice)
                    elif file_data['type'] == 'pdf':
                        res = edi_format.with_context(default_move_type=invoice.move_type).with_company(invoice.company_id)._update_invoice_from_pdf_reader(file_data['filename'], file_data['pdf_reader'], invoice)
                        file_data['pdf_reader'].stream.close()
                    else:  # file_data['type'] == 'binary'
                        res = edi_format._update_invoice_from_binary(file_data['filename'], file_data['content'], file_data['extension'], invoice)
                except Exception as e:
                    _logger.exception("Error importing attachment \"%s\" as invoice with format \"%s\"", file_data['filename'], edi_format.name, str(e))
                if res:
                    return res
        return self.env['account.move']

    ####################################################
    # Import helpers
    ####################################################

    def _find_value(self, xpath, xml_element, namespaces=None):
        element = xml_element.xpath(xpath, namespaces=namespaces)
        return element[0].text if element else None

    @api.model
    def _retrieve_partner_with_vat(self, vat, extra_domain):
        if not vat:
            return None

        # Sometimes, the vat is specified with some whitespaces.
        normalized_vat = vat.replace(' ', '')
        country_prefix = re.match('^[a-zA-Z]{2}|^', vat).group()

        partner = self.env['res.partner'].search(extra_domain + [('vat', 'in', (normalized_vat, vat))], limit=1)

        # Try to remove the country code prefix from the vat.
        if not partner and country_prefix:
            partner = self.env['res.partner'].search(extra_domain + [
                ('vat', 'in', (normalized_vat[2:], vat[2:])),
                ('country_id.code', '=', country_prefix.upper()),
            ], limit=1)

            # The country could be not specified on the partner.
            if not partner:
                partner = self.env['res.partner'].search(extra_domain + [
                    ('vat', 'in', (normalized_vat[2:], vat[2:])),
                    ('country_id', '=', False),
                ], limit=1)

            # The vat could be a string of alphanumeric values without country code but with missing zeros at the
            # beginning.
        if not partner:
            try:
                vat_only_numeric = str(int(re.sub(r'^\D{2}', '', normalized_vat) or 0))
            except ValueError:
                vat_only_numeric = None

            if vat_only_numeric:
                query = self.env['res.partner']._where_calc(extra_domain + [('active', '=', True)])
                tables, where_clause, where_params = query.get_sql()

                if country_prefix:
                    vat_prefix_regex = f'({country_prefix})?'
                else:
                    vat_prefix_regex = '([A-z]{2})?'

                self._cr.execute(f'''
                    SELECT res_partner.id
                    FROM {tables}
                    WHERE {where_clause}
                    AND res_partner.vat ~ %s
                    LIMIT 1
                ''', where_params + ['^%s0*%s$' % (vat_prefix_regex, vat_only_numeric)])
                partner_row = self._cr.fetchone()
                if partner_row:
                    partner = self.env['res.partner'].browse(partner_row[0])

        return partner

    @api.model
    def _retrieve_partner_with_phone_mail(self, phone, mail, extra_domain):
        domains = []
        if phone:
            domains.append([('phone', '=', phone)])
            domains.append([('mobile', '=', phone)])
        if mail:
            domains.append([('email', '=', mail)])

        if not domains:
            return None

        domain = expression.OR(domains)
        if extra_domain:
            domain = expression.AND([domain, extra_domain])
        return self.env['res.partner'].search(domain, limit=1)

    @api.model
    def _retrieve_partner_with_name(self, name, extra_domain):
        if not name:
            return None
        return self.env['res.partner'].search([('name', 'ilike', name)] + extra_domain, limit=1)

    def _retrieve_partner(self, name=None, phone=None, mail=None, vat=None, domain=None):
        '''Search all partners and find one that matches one of the parameters.
        :param name:    The name of the partner.
        :param phone:   The phone or mobile of the partner.
        :param mail:    The mail of the partner.
        :param vat:     The vat number of the partner.
        :returns:       A partner or an empty recordset if not found.
        '''

        def search_with_vat(extra_domain):
            return self._retrieve_partner_with_vat(vat, extra_domain)

        def search_with_phone_mail(extra_domain):
            return self._retrieve_partner_with_phone_mail(phone, mail, extra_domain)

        def search_with_name(extra_domain):
            return self._retrieve_partner_with_name(name, extra_domain)

        def search_with_domain(extra_domain):
            if not domain:
                return None
            return self.env['res.partner'].search(domain + extra_domain, limit=1)

        for search_method in (search_with_vat, search_with_domain, search_with_phone_mail, search_with_name):
            for extra_domain in ([('company_id', '=', self.env.company.id)], []):
                partner = search_method(extra_domain)
                if partner:
                    return partner
        return self.env['res.partner']

    def _retrieve_product(self, name=None, default_code=None, barcode=None):
        '''Search all products and find one that matches one of the parameters.

        :param name:            The name of the product.
        :param default_code:    The default_code of the product.
        :param barcode:         The barcode of the product.
        :returns:               A product or an empty recordset if not found.
        '''
        if name and '\n' in name:
            # cut Sales Description from the name
            name = name.split('\n')[0]
        domains = []
        for value, domain in (
            (name, ('name', 'ilike', name)),
            (default_code, ('default_code', '=', default_code)),
            (barcode, ('barcode', '=', barcode)),
        ):
            if value is not None:
                domains.append([domain])

        domain = expression.AND([
            expression.OR(domains),
            [('company_id', 'in', [False, self.env.company.id])],
        ])
        return self.env['product.product'].search(domain, limit=1)

    def _retrieve_tax(self, amount, type_tax_use):
        '''Search all taxes and find one that matches all of the parameters.

        :param amount:          The amount of the tax.
        :param type_tax_use:    The type of the tax.
        :returns:               A tax or an empty recordset if not found.
        '''
        domains = [
            [('amount', '=', float(amount))],
            [('type_tax_use', '=', type_tax_use)],
            [('company_id', '=', self.env.company.id)]
        ]

        return self.env['account.tax'].search(expression.AND(domains), order='sequence ASC', limit=1)

    def _retrieve_currency(self, code):
        '''Search all currencies and find one that matches the code.

        :param code: The code of the currency.
        :returns:    A currency or an empty recordset if not found.
        '''
        return self.env['res.currency'].with_context(active_test=False).search([('name', '=', code.upper())], limit=1)

    ####################################################
    # Other helpers
    ####################################################

    @api.model
    def _format_error_message(self, error_title, errors):
        bullet_list_msg = ''.join('<li>%s</li>' % html_escape(msg) for msg in errors)
        return '%s<ul>%s</ul>' % (error_title, bullet_list_msg)

    def _is_account_edi_ubl_cii_available(self):
        return hasattr(self, '_infer_xml_builder_from_tree')
