# -*- coding: utf-8 -*-

from odoo import _, api, models, tools
from odoo.addons.l10n_it_edi.tools.remove_signature import remove_signature
from odoo.exceptions import UserError

from lxml import etree
from io import BytesIO
import logging
import re

_logger = logging.getLogger(__name__)

FATTURAPA_FILENAME_RE = "[A-Z]{2}[A-Za-z0-9]{2,28}_[A-Za-z0-9]{0,5}.((?i:xml.p7m|xml))"


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def remove_xades_sign(self, xml):
        # Recovering parser is needed for files where strings like
        # xmlns:ds="http://www.w3.org/2000/09/xmldsig#&quot;"
        # are present: even if lxml raises
        # {XMLSyntaxError}xmlns:ds:
        # 'http://www.w3.org/2000/09/xmldsig#"' is not a valid URI
        # such files are accepted by SDI
        recovering_parser = etree.XMLParser(recover=True, resolve_entities=False)
        root = etree.XML(xml, parser=recovering_parser)
        for elem in root.iter("*"):
            if elem.tag.find("Signature") > -1:
                elem.getparent().remove(elem)
                break
            if any(" " in elem.nsmap[tag] for tag in elem.nsmap):
                etree.cleanup_namespaces(elem)
        return etree.tostring(root)

    def cleanup_xml(self, xml_string):
        xml_string = self.remove_xades_sign(xml_string)
        xml_string = remove_signature(xml_string)
        return xml_string

    def get_xml_string(self):
        data = self.raw

        try:
            return self.cleanup_xml(data)
        except AttributeError as e:
            raise UserError(_("Invalid xml %s.") % e.args) from e

    def get_fatturapa_preview_style_name(self):
        """ Hook to have a clean inheritance. """
        return "FoglioStileAssoSoftware.xsl"

    def get_fattura_elettronica_preview(self):
        xsl_path = tools.misc.file_path(
            f"l10n_it_edi/data/{self.get_fatturapa_preview_style_name()}"
        )
        xslt = etree.parse(xsl_path)
        xml_string = self.get_xml_string()
        xml_file = BytesIO(xml_string)
        recovering_parser = etree.XMLParser(recover=True, resolve_entities=False)
        dom = etree.parse(xml_file, parser=recovering_parser)
        transform = etree.XSLT(xslt)
        newdom = transform(dom)
        return etree.tostring(newdom, pretty_print=True, encoding="unicode")

    def _decode_edi_l10n_it_edi(self, name, content):
        """ Decodes a  into a list of one dictionary representing an attachment.
            :returns:           A list with a dictionary.
        """
        if not (decoded_content := remove_signature(content)):
            return []

        parser = etree.XMLParser(recover=True, resolve_entities=False)
        try:
            xml_tree = etree.fromstring(decoded_content, parser)
        except etree.ParseError as e:
            _logger.exception("Error when converting the xml content to etree: %s", e)
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
