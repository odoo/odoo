# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
            'xml_tree': xml_move_tree,
            'type': 'l10n_it_edi',
            'sort_weight': 11,
        } for xml_move_tree in xml_tree.xpath('//FatturaElettronicaBody')]

    def _l10n_it_edi_check_processable(self):
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
            'name': 'l10n_it_edi',
            'check': lambda a: a._l10n_it_edi_check_processable(),
            'decoder': self._decode_edi_l10n_it_edi,
        }] + super()._get_edi_supported_formats()

    @api.model
    def _l10n_it_edi_generate_filename(self, company):
        '''Returns a name conform to the Fattura pa Specifications:
           See ES documentation 2.2
        '''
        a = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        # Each company should have its own filename sequence. If it does not exist, create it
        n = self.env['ir.sequence'].with_company(company).next_by_code('l10n_it_edi.fattura_filename')
        if not n:
            # The offset is used to avoid conflicts with existing filenames
            offset = 62 ** 4
            sequence = self.env['ir.sequence'].sudo().create({
                'name': 'FatturaPA Filename Sequence',
                'code': 'l10n_it_edi.fattura_filename',
                'company_id': company.id,
                'number_next': offset,
            })
            n = sequence._next()
        # The n is returned as a string, but we require an int
        n = int(''.join(filter(lambda c: c.isdecimal(), n)))

        progressive_number = ""
        while n:
            (n, m) = divmod(n, len(a))
            progressive_number = a[m] + progressive_number

        return '%(country_code)s%(codice)s_%(progressive_number)s.xml' % {
            'country_code': company.country_id.code,
            'codice': company.partner_id._l10n_it_edi_normalized_codice_fiscale(),
            'progressive_number': progressive_number.zfill(5),
        }
