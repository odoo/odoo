# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64decode, b64encode
import gzip
import logging
from lxml import etree

from odoo import _
from odoo.tools import cleanup_xml_node
from odoo.addons.l10n_hu_edi.models.l10n_hu_edi_connection import L10nHuEdiConnection as BaseL10nHuEdiConnection, XML_NAMESPACES
from odoo.addons.l10n_hu_edi_receive.models.account_move import boolean

_logger = logging.getLogger(__name__)


class L10nHuEdiConnection(BaseL10nHuEdiConnection):

    def query_invoice_digest(self, credentials, datetime_from, datetime_to, page=1):
        template_values = {
            **self._get_header_values(credentials),
            'page': page,
            'invoiceDirection': 'INBOUND',
            'dateTimeFrom': datetime_from,
            'dateTimeTo': datetime_to,
        }
        request_data = self.env['ir.qweb']._render('l10n_hu_edi_receive.query_invoice_digest_request', template_values)
        request_data = etree.tostring(cleanup_xml_node(request_data, remove_blank_nodes=False), xml_declaration=True, encoding='UTF-8')

        response_xml = self._call_nav_endpoint(credentials['mode'], 'queryInvoiceDigest', request_data, timeout=60)
        func_code = response_xml.findtext('common:result/common:funcCode', namespaces=XML_NAMESPACES)

        if func_code == 'ERROR':
            _logger.error("Error in NAV invoice digest query: %s \n", "\n".join(self._get_errors(response_xml)))
            return func_code

        current_page = int(response_xml.findtext('api:invoiceDigestResult/api:currentPage', namespaces=XML_NAMESPACES))
        available_page = int(response_xml.findtext('api:invoiceDigestResult/api:availablePage', namespaces=XML_NAMESPACES))

        if available_page == 0:
            return func_code

        moves_vals = self.env['account.move']._l10n_hu_edi_get_moves_vals_from_digest(response_xml)
        self.env['account.move'].create(moves_vals)

        if current_page == available_page:
            return func_code

        return self.query_invoice_digest(credentials, datetime_from, datetime_to, page=current_page + 1)

    def query_invoice_data(self, credentials, moves):
        for move in moves:
            template_values = {
                **self._get_header_values(credentials),
                'invoiceNumber': move.ref,
                'invoiceDirection': 'INBOUND',
                'supplierTaxNumber': move.partner_id.vat[:8],
            }
            if l10n_hu_edi_batch_index := move.l10n_hu_edi_batch_index:
                template_values['batchIndex'] = l10n_hu_edi_batch_index

            request_data = self.env['ir.qweb']._render('l10n_hu_edi_receive.query_invoice_data_request', template_values)
            request_data = etree.tostring(cleanup_xml_node(request_data, remove_blank_nodes=False), xml_declaration=True, encoding='UTF-8')

            response_xml = self._call_nav_endpoint(credentials['mode'], 'queryInvoiceData', request_data, timeout=60)
            func_code = response_xml.findtext('common:result/common:funcCode', namespaces=XML_NAMESPACES)

            if func_code == 'ERROR':
                move.l10n_hu_edi_messages = {
                    'error_title': _("Error in NAV invoice data query."),
                    'errors': self._get_errors(response_xml),
                    'blocking_level': 'error',
                }
                continue

            invoice_data_b64 = response_xml.findtext('api:invoiceDataResult/api:invoiceData', namespaces=XML_NAMESPACES)
            if invoice_data_b64:
                if boolean(response_xml.findtext('api:invoiceDataResult/api:compressedContentIndicator', namespaces=XML_NAMESPACES)):
                    invoice_data_b64 = b64encode(gzip.decompress(b64decode(invoice_data_b64)))
                move.l10n_hu_edi_attachment = invoice_data_b64
                move.l10n_hu_edi_state = 'received'
                move.l10n_hu_edi_messages = False

    def _get_errors(self, response_xml):
        error_code = response_xml.findtext('common:result/common:errorCode', namespaces=XML_NAMESPACES)
        message = response_xml.findtext('common:result/common:message', namespaces=XML_NAMESPACES)
        errors = [f"{error_code}: {message}"]
        for message_xml in response_xml.iterfind('api:technicalValidationMessages', namespaces=XML_NAMESPACES):
            message = message_xml.findtext('api:message', namespaces=XML_NAMESPACES)
            error_code = message_xml.findtext('api:validationErrorCode', namespaces=XML_NAMESPACES)
            errors.append(f"{error_code}: {message}")

        return errors
