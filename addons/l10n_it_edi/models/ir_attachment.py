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

    def _get_xml_tree(self):
        """ Some FatturaPA XMLs need to be parsed with `recover=True`,
            and some have signatures that need to be removed prior to parsing.
        """
        # EXTENDS 'account'
        res = super()._get_xml_tree()

        # If the file was not correctly parsed, retry parsing it.
        if res is None and self._is_l10n_it_edi_import_file():
            def parse_xml(parser, name, content):
                try:
                    return etree.fromstring(content, parser)
                except (etree.ParseError, ValueError) as e:
                    _logger.info("XML parsing of %s failed: %s", name, e)

            parser = etree.XMLParser(recover=True, resolve_entities=False)
            xml_tree = (
                parse_xml(parser, self.name, self.raw)
                # The file may have a Cades signature, so we try removing it.
                or parse_xml(parser, self.name, remove_signature(self.raw))
            )
            if xml_tree is None:
                _logger.info("Italian EDI invoice file %s cannot be decoded.", self.name)
            return xml_tree

        return res

    def _is_l10n_it_edi_import_file(self):
        is_xml = (
            self.name.endswith('.xml')
            or self.mimetype.endswith('/xml')
            or 'text/plain' in self.mimetype
            and self.raw
            and self.raw.startswith(b'<?xml'))
        is_p7m = self.mimetype == 'application/pkcs7-mime'
        return (is_xml or is_p7m) and re.search(FATTURAPA_FILENAME_RE, self.name)

    def _get_import_type_and_priority(self):
        """ Identify FatturaPA XML and P7M files. """
        # EXTENDS 'account'
        if self._is_l10n_it_edi_import_file() and self.xml_tree is not False:
            return ('l10n_it.fatturapa', 20)
        return super()._get_import_type_and_priority()

    def _unwrap_attachment(self):
        """ Divide a FatturaPA file into constituent invoices and create a new attachment for each invoice after the first. """
        # EXTENDS 'account'
        if self.import_type == 'l10n_it.fatturapa' and len(self.xml_tree.findall('.//FatturaElettronicaBody')) > 1:
            # One FatturaPA file may contain multiple invoices. In that case, create an
            # attachment for each invoice beyond the first. We don't set the `root_attachment_id`
            # field on those attachments to make sure they are not grouped with the original file,
            # and we also create them as database records so that they persist on the invoice chatter.

            # Create a new xml tree for each invoice beyond the first
            trees = split_etree_on_tag(self.xml_tree, 'FatturaElettronicaBody')
            filename_without_extension, dummy, extension = self.name.rpartition('.')
            attachment_vals = [
                {
                    'name': f'{filename_without_extension}_{filename_index}.{extension}',
                    'raw': etree.tostring(tree),
                    'xml_tree': tree,
                }
                for filename_index, tree in enumerate(trees[1:], start=2)
            ]
            return self.create(attachment_vals)

        return super()._unwrap_attachment()
