from odoo import models
from odoo.addons.l10n_it_edi.tools.remove_signature import remove_signature

from copy import deepcopy
from lxml import etree
import logging
import re

_logger = logging.getLogger(__name__)

FATTURAPA_FILENAME_RE = "[A-Z]{2}[A-Za-z0-9]{2,28}_[A-Za-z0-9]{0,5}.((?i:xml.p7m|xml))"


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _identify_and_unwrap_file(self, file_data):
        """ Identify FatturaPA XML and P7M files.

        Additionally, divide them into constituent invoices and create a new attachment for each invoice after the first.
        """
        # EXTENDS 'account'
        if self._is_l10n_it_edi_import_file():

            # If the file was not correctly parsed, retry parsing it.
            if (xml_tree := file_data.get('xml_tree')) is None:
                def parse_xml(parser, name, content):
                    try:
                        return etree.fromstring(content, parser)
                    except (etree.ParseError, ValueError) as e:
                        _logger.info("XML parsing of %s failed: %s", name, e)

                parser = etree.XMLParser(recover=True, resolve_entities=False)
                xml_tree = (
                    parse_xml(parser, file_data['filename'], file_data['content'])
                    # The file may have a Cades signature, so we try removing it.
                    or parse_xml(parser, file_data['filename'], remove_signature(file_data['content']))
                )

            if xml_tree is not None:
                file_data |= {'type': 'l10n_it.fatturapa', 'priority': 20}
                files_data = [{**file_data, 'xml_tree': xml_tree}]

                # One FatturaPA file may contain multiple invoices. In that case, we create new
                # attachments for each of the invoices after the first, that contain only the data
                # for that invoice.
                if len(xml_tree.findall('.//FatturaElettronicaBody')) > 1:
                    xml_tree_without_invoices = deepcopy(xml_tree)
                    invoice_nodes = xml_tree_without_invoices.findall('.//FatturaElettronicaBody')
                    parent_node = invoice_nodes[0].getparent()

                    for invoice_node in invoice_nodes:
                        parent_node.remove(invoice_node)

                    for filename_index, invoice_node in enumerate(invoice_nodes, start=2):
                        parent_node.append(invoice_node)
                        xml_tree_copy = deepcopy(xml_tree_without_invoices)
                        parent_node.remove(invoice_node)

                        content = etree.tostring(xml_tree_copy)

                        # Create a new attachment with the edited XML.
                        filename, dummy, extension = file_data['filename'].rpartition('.')
                        new_filename = f'{filename}_{filename_index}.{extension}'
                        new_attachment = self.create({
                            'name': new_filename,
                            'raw': content,
                            'type': 'binary',
                        })
                        files_data.append({
                            **file_data,
                            'content': content,
                            'filename': new_filename,
                            'attachment': new_attachment,
                            'xml_tree': xml_tree_copy,
                        })

                    return files_data

            else:
                _logger.info("Italian EDI invoice file %s cannot be decoded.", file_data['filename'])

        return super()._identify_and_unwrap_file(file_data)

    def _is_l10n_it_edi_import_file(self):
        is_p7m = self.mimetype == 'application/pkcs7-mime'
        return (self._is_xml() or is_p7m) and re.search(FATTURAPA_FILENAME_RE, self.name)
