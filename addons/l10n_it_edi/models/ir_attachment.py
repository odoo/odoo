# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.addons.l10n_it_edi.tools.remove_signature import remove_signature

from lxml import etree
import logging

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def _decode_edi_xml_p7m(self, filename, content):
        """Decodes an xml.p7m into a list of one dictionary representing an attachment.
        :returns:           A list with a dictionary.
        """
        decoded_content = remove_signature(content)
        if not decoded_content:
            return

        try:
            parser = etree.XMLParser(recover=True)
            xml_tree = etree.fromstring(decoded_content, parser)
        except Exception as e:
            _logger.exception("Error when converting the xml content to etree: %s", e)
            return []

        to_process = []
        if xml_tree is not None:
            to_process.append({
                'filename': filename,
                'content': content,
                'xml_tree': xml_tree,
                'type': 'xml_p7m',
                'sort_weight': 11,
            })
        return to_process

    @api.model
    def _get_edi_supported_formats(self):
        # EXTENDS 'account'
        decoders = super()._get_edi_supported_formats()
        decoders.append({
            'check': lambda attachment: attachment.name.endswith('.xml.p7m'),
            'decoder': self._decode_edi_xml_p7m,
        })
        return decoders
