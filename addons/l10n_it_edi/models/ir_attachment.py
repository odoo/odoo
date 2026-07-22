# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.addons.l10n_it_edi.tools.remove_signature import remove_signature
from odoo.tools.mimetypes import guess_mimetype

from lxml import etree
import logging

_logger = logging.getLogger(__name__)

FATTURAPA_FILENAME_RE = "[A-Z]{2}[A-Za-z0-9]{2,28}_[A-Za-z0-9]{0,5}.((?i:xml.p7m|xml))"


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _parse_xml_with_recovery(self, content, name=None):
        def parse_xml(parser, content):
            try:
                return etree.fromstring(content, parser)
            except (etree.ParseError, ValueError, TypeError) as e:
                # Note: lxml < 5.0 raises ValueError; lxml 5.0+ / libxml2 2.12+ raises TypeError
                _logger.info("XML parsing of %s failed: %s", name, e)

        parser = etree.XMLParser(recover=True, resolve_entities=False)
        xml_tree = parse_xml(parser, content)

        if xml_tree is None:
            cleaned = remove_signature(content)
            if cleaned:
                xml_tree = parse_xml(parser, cleaned)

        return xml_tree

    def _decode_edi_l10n_it_edi(self, name, content):
        """ Tries to decode the content of the file being imported
            into a list of one dictionary representing an attachment.
            :returns:           A list with a dictionary.
        """
        xml_tree = self._parse_xml_with_recovery(content, name)

        if xml_tree is None or not etree.QName(xml_tree).localname.startswith('FatturaElettronica'):
            _logger.info("Italian EDI invoice file %s cannot be decoded.", name)
            return []

        return [{
            'filename': name,
            'content': content,
            'attachment': self,
            'xml_tree': xml_tree,
            'type': 'l10n_it_edi',
            'sort_weight': 11,
        }]

    def _is_l10n_it_edi_import_file(self):
        """ Determine whether the attachment contains a supported Italian EDI XML or P7M file."""

        if self.raw and (
            self.mimetype.endswith('/xml')
            or 'application/pkcs7-mime' in self.mimetype
            or (
                'text/plain' in self.mimetype
                and (
                    self.name.lower().endswith(('.xml', '.p7m'))
                    or guess_mimetype(self.raw or b'').endswith('/xml')
                )
            )
        ):
            xml_tree = self._parse_xml_with_recovery(self.raw, self.name)
            if xml_tree is not None:
                return etree.QName(xml_tree).localname.startswith('FatturaElettronica')

        return False

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
