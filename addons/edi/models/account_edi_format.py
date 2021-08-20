# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.tools.pdf import OdooPdfFileReader
from odoo.osv import expression
from odoo.tools import html_escape

from lxml import etree
import base64
import io
import logging
import pathlib

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

        # activate cron
        if any(edi_format._needs_web_services() for edi_format in edi_formats):
            self.env.ref('edi.ir_cron_edi_network').active = True

        return edi_formats

    ####################################################
    # Export method to override based on EDI Format
    ####################################################

    def _get_edi_priority(self):
        """Set priority between the different edi types. The lower priority will be processed first.

        :returns:   A dictionary {edi_type: priority}
        * edi_type: The type of the edi (for example: invoice, payment, picking).
        * priority: An integer.
        """
        # TO OVERRIDE
        return {}

    def _is_required_for_record(self, rec, edi_type):
        """ Indicate if this EDI must be generated for the record passed as parameter.

        :param rec:      A record.
        :param edi_type: The type of the edi (for example: invoice, payment, picking).
        :returns:        True if the EDI must be generated, False otherwise.
        """
        # TO OVERRIDE
        self.ensure_one()
        return True

    def _needs_web_services(self):
        """ Indicate if the EDI must be generated asynchronously through to some web services.

        :return: True if such a web service is available, False otherwise.
        """
        self.ensure_one()
        return False

    def _support_batching(self, rec, edi_type, state, company):
        """ Indicate if we can send multiple documents in the same time to the web services.
        If True, the _post_edi method will get multiple documents in the same time.
        Otherwise, these methods will be called with only one record at a time.

        :param rec:      The record that we are trying to batch.
        :param edi_type: The type of the edi (for example: invoice, payment, picking).
        :param state:    The EDI state of the record.
        :param company:  The company with which we are sending the EDI.
        :returns:        True if batching is supported, False otherwise.
        """
        # TO OVERRIDE
        return False

    def _get_batch_key(self, rec, edi_type, state):
        """ Returns a tuple that will be used as key to partitionnate the records when creating batches
        with multiple records.
        The type of the edi, its company_id, its edi state and the edi_format are used by default, if
        no further partition is needed for this format, this method should return (). It's not necessary to repeat those
        fields in the custom key.

        :param rec:      The record to batch.
        :param edi_type: The type of the edi (for example: invoice, payment, picking).
        :param state:    The EDI state of the record.
        :returns:        The key to be used when partitionning the batches.
        """
        rec.ensure_one()
        return ()

    def _check_record_configuration(self, rec, edi_type):
        """ Checks the record and relevant records for potential error (missing data, etc).

        :param rec:      The record to check.
        :param edi_type: The type of the edi (for example: invoice, payment, picking).
        :returns:        A list of error messages.
        """
        # TO OVERRIDE
        return []

    def _post_edi(self, recs, edi_type):
        """ Create the file content representing the record (and calls web services if necessary).

        :param recs:        A list of records to post.
        :param edi_type:    The type of the edi (for example: invoice, payment, picking).
        :returns:           A dictionary with the records as key and as value, another dictionary:
        * success:          True if the edi was successfully posted.
        * attachment:       The attachment representing the record in this edi_format.
        * error:            An error if the edi was not successfully posted.
        * blocking_level:   (optional) How bad is the error (how should the edi flow be blocked ?)
        """
        # TO OVERRIDE
        self.ensure_one()
        return {}

    def _cancel_edi(self, recs, edi_type):
        """Calls the web services to cancel the record in the web service.

        :param recs:        A list of records to cancel.
        :param edi_type:    The type of the edi (for example: invoice, payment, picking).
        :returns:           A dictionary with the records as key and as value, another dictionary:
        * success:          True if the record was successfully cancelled.
        * error:            An error if the edi was not successfully cancelled.
        * blocking_level:   (optional) How bad is the error (how should the edi flow be blocked ?)
        """
        # TO OVERRIDE
        self.ensure_one()
        return {rec: {'success': True} for rec in recs}  # By default, cancel succeeds doing nothing.

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
            _logger.exception("Error when converting the xml content to etree: %s", e)
            return to_process
        if len(xml_tree) > 0:
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
            _logger.exception("Error when reading the pdf: %s", e)
            return to_process

        # Process embedded files.
        try:
            for xml_name, content in pdf_reader.getAttachments():
                to_process.extend(self._decode_xml(xml_name, content))
        except NotImplementedError as e:
            _logger.warning("Unable to access the attachments of %s. Tried to decrypt it, but %s.", filename, e)

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

        if 'pdf' in attachment.mimetype:
            to_process.extend(self._decode_pdf(attachment.name, content))
        elif 'xml' in attachment.mimetype:
            to_process.extend(self._decode_xml(attachment.name, content))
        else:
            to_process.extend(self._decode_binary(attachment.name, content))

        return to_process

    ####################################################
    # Import helpers
    ####################################################

    def _find_value(self, xpath, xml_element, namespaces=None):
        element = xml_element.xpath(xpath, namespaces=namespaces)
        return element[0].text if element else None

    def _retrieve_partner(self, name=None, phone=None, mail=None, vat=None, domain=None):
        '''Search all partners and find one that matches one of the parameters.

        :param name:    The name of the partner.
        :param phone:   The phone or mobile of the partner.
        :param mail:    The mail of the partner.
        :param vat:     The vat number of the partner.
        :returns:       A partner or an empty recordset if not found.
        '''
        domains = []
        for value, dom in (
            (name, [('name', 'ilike', name)]),
            (phone, expression.OR([[('phone', '=', phone)], [('mobile', '=', phone)]])),
            (mail, [('email', '=', mail)]),
            (vat, [('vat', 'like', vat)]),
        ):
            if value is not None:
                domains.append(dom)

        if domain:
            domains.append(domain)

        domain = expression.OR(domains)
        return self.env['res.partner'].search(domain, limit=1)

    def _retrieve_product(self, name=None, default_code=None, barcode=None):
        '''Search all products and find one that matches one of the parameters.

        :param name:            The name of the product.
        :param default_code:    The default_code of the product.
        :param barcode:         The barcode of the product.
        :returns:               A product or an empty recordset if not found.
        '''
        domains = []
        for value, domain in (
            (name, ('name', 'ilike', name)),
            (default_code, ('default_code', '=', default_code)),
            (barcode, ('barcode', '=', barcode)),
        ):
            if value is not None:
                domains.append([domain])

        domain = expression.OR(domains)
        return self.env['product.product'].search(domain, limit=1)

    def _retrieve_tax(self, amount, type_tax_use):
        '''Search all taxes and find one that matches all of the parameters.

        :param amount:          The amount of the tax.
        :param type_tax_use:    The type of the tax.
        :returns:               A tax or an empty recordset if not found.
        '''
        domains = [
            [('amount', '=', float(amount))],
            [('type_tax_use', '=', type_tax_use)]
        ]

        return self.env['account.tax'].search(expression.AND(domains), order='sequence ASC', limit=1)

    def _retrieve_currency(self, code):
        '''Search all currencies and find one that matches the code.

        :param code: The code of the currency.
        :returns:    A currency or an empty recordset if not found.
        '''
        return self.env['res.currency'].search([('name', '=', code.upper())], limit=1)

    ####################################################
    # Other helpers
    ####################################################

    @api.model
    def _format_error_message(self, error_title, errors):
        bullet_list_msg = ''.join('<li>%s</li>' % html_escape(msg) for msg in errors)
        return '%s<ul>%s</ul>' % (error_title, bullet_list_msg)
