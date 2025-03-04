from odoo import models
from odoo.addons.l10n_it_edi.tools.remove_signature import remove_signature
from odoo.addons.account.models.ir_attachment import split_etree_on_tag

from lxml import etree
import logging
import re

_logger = logging.getLogger(__name__)

FATTURAPA_FILENAME_RE = "[A-Z]{2}[A-Za-z0-9]{2,28}_[A-Za-z0-9]{0,5}.((?i:xml.p7m|xml))"


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _get_xml_tree(self, file_data):
        """ Some FatturaPA XMLs need to be parsed with `recover=True`,
            and some have signatures that need to be removed prior to parsing.
        """
        # EXTENDS 'account'
        res = super()._get_xml_tree(file_data)

        # If the file was not correctly parsed, retry parsing it.
        if res is None and self._is_l10n_it_edi_import_file(file_data):
            def parse_xml(parser, name, content):
                try:
                    return etree.fromstring(content, parser)
                except (etree.ParseError, ValueError) as e:
                    _logger.info("XML parsing of %s failed: %s", name, e)

            parser = etree.XMLParser(recover=True, resolve_entities=False)
            xml_tree = (
                parse_xml(parser, file_data['name'], file_data['raw'])
                # The file may have a Cades signature, so we try removing it.
                or parse_xml(parser, file_data['name'], remove_signature(file_data['raw']))
            )
            if xml_tree is None:
                _logger.info("Italian EDI invoice file %s cannot be decoded.", file_data['name'])
            return xml_tree

        return res

    def _is_l10n_it_edi_import_file(self, file_data):
        is_xml = (
            file_data['name'].endswith('.xml')
            or file_data['mimetype'].endswith('/xml')
            or 'text/plain' in file_data['mimetype']
            and file_data['raw']
            and file_data['raw'].startswith(b'<?xml'))
        is_p7m = file_data['mimetype'] == 'application/pkcs7-mime'
        return (is_xml or is_p7m) and re.search(FATTURAPA_FILENAME_RE, file_data['name'])

    def _get_import_type_and_priority(self, file_data):
        """ Identify FatturaPA XML and P7M files. """
        # EXTENDS 'account'
        if self._is_l10n_it_edi_import_file(file_data) and file_data['xml_tree'] is not None:
            return ('l10n_it.fatturapa', 20)
        return super()._get_import_type_and_priority(file_data)

    def _unwrap_attachments(self, files_data, recurse=True):
        """ Divide a FatturaPA file into constituent invoices and create a new attachment for each invoice after the first. """
        # EXTENDS 'account'
        embedded = super()._unwrap_attachments(files_data, recurse=False)

        for file_data in files_data:
            if file_data['import_type'] == 'l10n_it.fatturapa' and len(file_data['xml_tree'].findall('.//FatturaElettronicaBody')) > 1:
                # One FatturaPA file may contain multiple invoices. In that case, create an
                # attachment for each invoice beyond the first.

                # Create a new xml tree for each invoice beyond the first
                trees = split_etree_on_tag(file_data['xml_tree'], 'FatturaElettronicaBody')
                filename_without_extension, dummy, extension = file_data['name'].rpartition('.')
                attachment_vals = [
                    {
                        'name': f'{filename_without_extension}_{filename_index}.{extension}',
                        'raw': etree.tostring(tree),
                    }
                    for filename_index, tree in enumerate(trees[1:], start=2)
                ]
                created_attachments = self.create(attachment_vals)

                embedded.extend(created_attachments._to_files_data())

        if embedded and recurse:
            embedded.extend(self._unwrap_attachments(embedded, recurse=True))
        return embedded
