# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo.tools import cleanup_xml_node
from odoo.addons.l10n_hu_edi.models.l10n_hu_edi_connection import L10nHuEdiConnection as BaseL10nHuEdiConnection


class L10nHuEdiConnection(BaseL10nHuEdiConnection):

    def query_invoice_digest(self, credentials, datetime_from, datetime_to, page, company):
        template_values = {
            **self._get_header_values(credentials),
            'page': page,
            'invoiceDirection': 'INBOUND',
            'dateTimeFrom': datetime_from,
            'dateTimeTo': datetime_to,
        }
        request_data = self.env['ir.qweb']._render('l10n_hu_edi_receive.query_invoice_digest_request', template_values)
        request_data = etree.tostring(cleanup_xml_node(request_data, remove_blank_nodes=False), xml_declaration=True, encoding='UTF-8')

        response_xml = self._call_nav_endpoint(credentials['mode'], 'queryInvoiceDigest', request_data, timeout=(20, 60))
        self._parse_error_response(response_xml)

        current_page = int(response_xml.findtext('{*}invoiceDigestResult/{*}currentPage'))
        available_page = int(response_xml.findtext('{*}invoiceDigestResult/{*}availablePage'))

        digests = self.env['account.move']._l10n_hu_edi_parse_digest_response(response_xml, company)

        return digests, current_page < available_page

    def query_invoice_data(self, credentials, digests, company):
        moves_vals_list = []
        post_process_data_list = []
        for query_invoice_data_params in digests:
            template_values = {
                **self._get_header_values(credentials),
                **query_invoice_data_params,
            }

            request_data = self.env['ir.qweb']._render('l10n_hu_edi_receive.query_invoice_data_request', template_values)
            request_data = etree.tostring(cleanup_xml_node(request_data, remove_blank_nodes=False), xml_declaration=True, encoding='UTF-8')

            response_xml = self._call_nav_endpoint(credentials['mode'], 'queryInvoiceData', request_data, timeout=(20, 60))
            self._parse_error_response(response_xml)

            moves_vals, post_process_data = self.env['account.move']._l10n_hu_edi_parse_query_invoice_data_response(response_xml, company)
            moves_vals_list.extend(moves_vals)
            post_process_data_list.extend(post_process_data)

        return moves_vals_list, post_process_data_list
