# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.addons.l10n_it_edi.tools.remove_signature import remove_signature

from lxml import etree
import logging
import re

_logger = logging.getLogger(__name__)

FATTURAPA_FILENAME_RE = "[A-Z]{2}[A-Za-z0-9]{2,28}_[A-Za-z0-9]{0,5}.((?i:xml.p7m|xml))"


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _decode_edi_l10n_it_edi(self, name, content):
        """ Decodes a  into a list of one dictionary representing an attachment.
            :returns:           A list with a dictionary.
        """
        def parse_xml(parser, name, content):
            try:
                return etree.fromstring(content, parser)
            except (etree.ParseError, ValueError) as e:
                _logger.info("XML parsing of %s failed: %s", name, e)

        parser = etree.XMLParser(recover=True, resolve_entities=False)
        if (xml_tree := parse_xml(parser, name, content)) is None:
            # The file may have a Cades signature, trying to remove it
            if (xml_tree := parse_xml(parser, name, remove_signature(content))) is None:
                _logger.info("Italian EDI invoice file %s cannot be decoded.", name)
                return []

        return [{
            'filename': name,
            'content': content,
            'attachment': self,
            'xml_tree': xml_move_tree,
            'type': 'l10n_it_edi',
            'sort_weight': 11,
        } for xml_move_tree in xml_tree.xpath('//FatturaElettronicaBody')]

    def _is_l10n_it_edi_import_file(self):
        is_xml = (
            self.name.endswith('.xml')
            or self.mimetype.endswith('/xml')
            or 'text/plain' in self.mimetype
            and self.raw
            and self.raw.startswith(b'<?xml'))
        is_p7m = self.mimetype == 'application/pkcs7-mime'
        return (is_xml or is_p7m) and re.search(FATTURAPA_FILENAME_RE, self.name)

    @api.model
    def _get_edi_supported_formats(self):
        """ XML files could be l10n_it_edi related or not, so check it
            before demanding the decoding to the the standard XML methods.
        """
        # EXTENDS 'account'
        return [{
            'format': 'l10n_it_edi',
            'check': lambda a: a._is_l10n_it_edi_import_file(),
            'decoder': self._decode_edi_l10n_it_edi,
        }] + super()._get_edi_supported_formats()
