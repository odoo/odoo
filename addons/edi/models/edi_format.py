# -*- encoding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import RedirectWarning
from odoo.tools.pdf import OdooPdfFileReader
from odoo.tools import html_escape
from odoo.osv import expression

from lxml import etree
import base64
import io
import logging
import pathlib
import re

_logger = logging.getLogger(__name__)


class EdiFormat(models.Model):
    """ Define an edi format, describing the flows and steps to take to create a document for it.
    """
    _name = 'edi.format'
    _description = 'EDI format'

    name = fields.Char()
    code = fields.Char(required=True)
    applicability = fields.Char(
        help="Technical field used to determine the applicability of an edi format. "
             "Should be a comma separated list: E.g. 'invoices, documents, sales_order'"
    )

    _sql_constraints = [
        ('unique_code', 'unique (code)', 'This EDI code already exists')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        edi_formats = super().create(vals_list)

        # Make sure the cron is running when using any edi that needs web services.
        if any(edi_format._get_edi_format_settings().get('needs_web_services') for edi_format in edi_formats):
            self.env.ref('edi.ir_cron_edi_network').active = True

        return edi_formats

    def _is_format_applicable(self, target):
        """ Determine if the format is applicable for the target.

        Use this to allow to filter the availability of the format. E.g. Used for accounting edi to determine if available
        on a specific journal.
        :param target: The target on which we want to see if the edi is applicable to.
        :return: True if the format is applicable
        """
        return True

    def _is_format_available_by_default(self, target):
        """ Determine if the format is available by default on the target.

        E.g. Used for accounting edi to determine if available by default on a specific journal.
        :param target: The target on which we want to see if the edi is available by default.
        :return: True if the format is available by default
        """
        return True

    def _is_format_required(self, document, document_type=''):
        """ Determine if the edi is required  for this document.

        :param document: The targeted business object
        :param document_type: Optional type of object (E.g. helps distinguish between invoice and payment for accounting)
        :return: True if the format is required
        """
        self.ensure_one()
        return True

    def _get_edi_format_settings(self, document=None, stage=None, flow_type=None):
        """ Return a dynamic dictionnary, containing the various settings for this edi format.
        Settings should be returned in a dict, as such:
        {
            'needs_web_services': True,
            'batching_key': 'batching_key',  # If set, it means batching is supported for this format/flow
            'document_needs_embedding': True,
            'attachments_required_in_mail': True,
            'stages': {
                'send': {  # Stages used for the send flow
                    'stage_one': {
                        'is_official': True,  # If True, the document becomes official after this step.
                        'message_to_log': 'Stage done',  # To log in the chatter once this stage is done.
                        'new_state': 'sent',  # Correspond to edi.flow.state, the state to set once this stage is done.
                        'id_error': 'stage_zero'  # In case of errors, go back to the targeted state
                        'action': _do_things,  # A method to call when executing this stage
                        'next_stage': '...'  # Optional, the next stage to execute
                    }
                },
                'cancel': ...  # Stages used for the cancel flow
            }
        }

        Some settings need computing, like support_batching/batching_key/...
        These should be computed in this method and returned along the other settings.
        todo We usually only need a specific key from the dict and recomputing it all may be overkill?
        """
        self.ensure_one()
        return {}

    def _check_document_configuration(self, document):
        """ Checks the document and linked record for potential error (missing data, etc).
        """
        self.ensure_one()
        return []

    def _import_document_from_xml_tree(self, filename, tree):
        """ Create a new document with the data inside the xml.
        """
        self.ensure_one()
        return False

    def _update_document_from_xml_tree(self, filename, tree, document):
        """ Update an existing invoice with the data contained in the xml.
        """
        self.ensure_one()
        return False

    def _import_document_from_pdf_reader(self, filename, tree):
        """ Create a new document with the data inside the xml.
        """
        self.ensure_one()
        return False

    def _update_document_from_pdf_reader(self, filename, tree, document):
        """ Update an existing invoice with the data contained in the xml.
        """
        self.ensure_one()
        return False

    def _import_document_from_binary(self, filename, tree, extension):
        """ Create a new document with the data inside the xml.
        """
        self.ensure_one()
        return False

    def _update_document_from_binary(self, filename, tree, extension, document):
        """ Update an existing invoice with the data contained in the xml.
        """
        self.ensure_one()
        return False

    def _decode_xml(self, filename, content):
        """Decodes a xml into a list of one dictionary representing an attachment.
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
        if xml_tree is not None:
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

    def _create_document_from_attachment(self, attachment):
        """ Decodes an ir.attachment and returns the newly created document.
        The type of document may change depending on the edi format that is used.
        """
        for file_data in self._decode_attachment(attachment):
            for edi_format in self:
                res = {}
                try:
                    if file_data['type'] == 'xml':
                        res = edi_format.with_company(self.env.company)._import_document_from_xml_tree(file_data['filename'], file_data['xml_tree'])
                    elif file_data['type'] == 'pdf':
                        res = edi_format.with_company(self.env.company)._import_document_from_pdf_reader(file_data['filename'], file_data['pdf_reader'])
                        file_data['pdf_reader'].stream.close()
                    else:
                        res = edi_format._import_document_from_binary(file_data['filename'], file_data['content'], file_data['extension'])
                except RedirectWarning as rw:
                    raise rw
                except Exception as e:
                    _logger.exception("Error importing attachment \"%s\" with format \"%s\": %s", file_data['filename'], edi_format.name, str(e))
                if res:
                    return res
        return {}

    def _update_document_from_attachment(self, attachment, document):
        """Decodes an ir.attachment to update a document.
        :param attachment:  An ir.attachment record.
        :returns:           The document where to import data.
        """
        for file_data in self._decode_attachment(attachment):
            for edi_format in self:
                res = False
                try:
                    # todo fix, probably wrong, to be tested. We should accept xml files labelled as .txt for security reasons. Also adapt other methods like this one.
                    if file_data['type'] == 'xml' or (file_data['type'] == 'txt' and file_data['content'].startswith(b'<?xml')):
                        res = edi_format.with_company(self.env.company)._update_document_from_xml_tree(file_data['filename'], file_data['xml_tree'], document)
                    elif file_data['type'] == 'pdf':
                        res = edi_format.with_company(self.env.company)._update_document_from_pdf_reader(file_data['filename'], file_data['pdf_reader'], document)
                        file_data['pdf_reader'].stream.close()
                    else:  # file_data['type'] == 'binary'
                        res = edi_format._update_document_from_binary(file_data['filename'], file_data['content'], file_data['extension'], document)
                except Exception as e:
                    _logger.exception("Error importing attachment \"%s\" as document with format \"%s\": %s", file_data['filename'], edi_format.name, str(e))
                if res:
                    return res
        return self.env[document._name]

    def _prepare_document_report(self, pdf_writer, edi_files):
        """
        Prepare a document report to be printed.
        :param pdf_writer: The pdf writer with the document pdf content loaded.
        :param edi_files: The edi file to be added to the pdf file.
        """
        # TO OVERRIDE
        self.ensure_one()

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
        def search_with_vat(extra_domain):
            if not vat:
                return None

            # Sometimes, the vat is specified with some whitespaces.
            normalized_vat = vat.replace(' ', '')
            country_prefix = re.match('^[A-Z]{2}|^', vat, re.I).group()

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
                        vat_prefix_regex = '([A-Z]{2})?'

                    self._cr.execute(f'''
                        SELECT res_partner.id
                        FROM {tables}
                        WHERE {where_clause}
                        AND res_partner.vat ~* %s
                        LIMIT 1
                    ''', where_params + ['^%s0*%s$' % (vat_prefix_regex, vat_only_numeric)])
                    partner_row = self._cr.fetchone()
                    if partner_row:
                        partner = self.env['res.partner'].browse(partner_row[0])

            return partner

        def search_with_phone_mail(extra_domain):
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

        def search_with_name(extra_domain):
            if not name:
                return None
            return self.env['res.partner'].search([('name', 'ilike', name)] + extra_domain, limit=1)

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
        '''Search all taxes and find one that matches all the parameters.
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
        return self.env['res.currency'].with_context(active_test=False).search([('name', '=', code.upper())], limit=1)

    ####################################################
    # Other helpers
    ####################################################

    @api.model
    def _format_error_message(self, error_title, errors):
        bullet_list_msg = ''.join('<li>%s</li>' % html_escape(msg) for msg in errors)
        return '%s<ul>%s</ul>' % (error_title, bullet_list_msg)
