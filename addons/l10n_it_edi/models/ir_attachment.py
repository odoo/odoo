from odoo import models
from odoo.addons.l10n_it_edi.tools.remove_signature import remove_signature

from lxml import etree
import logging
import re

_logger = logging.getLogger(__name__)

FATTURAPA_FILENAME_RE = "[A-Z]{2}[A-Za-z0-9]{2,28}_[A-Za-z0-9]{0,5}.((?i:xml.p7m|xml))"


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _identify_and_unwrap_file(self, file_data):
        """ If the file is a FatturaPA XML or P7M:
            - divide it into its constituent invoices;
            - create a new attachment for each invoice after the first; and
            - set the decoder.
        """
        # EXTENDS 'account'
        if self._is_l10n_it_edi_import_file():

            # If the file was not correctly parsed, retry parsing it.
            if not (xml_tree := file_data.get('xml_tree')):
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

            if xml_tree:
                file_data |= {
                    'type': 'l10n_it.fatturapa',
                    'decoder': self.env['account.move']._l10n_it_edi_import_invoice,
                    'priority': 20,
                }
                files_data = [{**file_data, 'xml_tree': xml_tree}]

                # One FatturaPA file may contain multiple invoices, so we may need to split it.
                # To do that, we pop off the `FatturaElettronicaBody` nodes one by one until none are left.
                content = etree.tostring(xml_tree)
                xml_tree = etree.fromstring(content)  # This effectively does a copy of the etree.

                index = 2
                while invoice_node := xml_tree.find('//FatturaElettronicaBody'):
                    invoice_node.getparent().remove(invoice_node)
                    content = etree.tostring(xml_tree)

                    # Create a new attachment with the edited XML.
                    filename, dummy, extension = file_data['filename'].rpartition('.')
                    new_filename = f'{filename}_{index}.{extension}'
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
                    })

                    xml_tree = etree.fromstring(content)
                    index += 1

                return files_data

            else:
                _logger.info("Italian EDI invoice file %s cannot be decoded.", file_data['filename'])

        return super()._identify_and_unwrap_file(file_data)

    def _is_l10n_it_edi_import_file(self):
        is_p7m = self.mimetype == 'application/pkcs7-mime'
        return (self._is_xml() or is_p7m) and re.search(FATTURAPA_FILENAME_RE, self.name)
