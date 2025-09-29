import logging
import re
import xml.etree.ElementTree as ET
from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)

# Documentation: https://files.support.epson.com/pdf/pos/bulk/tm-int_sdp_um_e_reve.pdf
EPSON_ERRORS = {
    'EPTR_AUTOMATICAL': 'Continuous printing of high-density printing caused a printing error',
    'EPTR_COVER_OPEN': 'Printer cover is open, please close it before printing',
    'EPTR_CUTTER': 'The cutter has a foreign matter, please check the cutter mechanism',
    'EPTR_MECHANICAL': 'Mechanical error, please check the printer',
    'EPTR_REC_EMPTY': 'The paper is empty, please load paper into the printer',
    'EPTR_UNRECOVERABLE': 'Low voltage unrecoverable error occured, please check the printer',
    'EX_BADPORT': 'The device is not connected, please check the printer power / connection',
    'EX_TIMEOUT': 'Print timeout occured, please try again',
}


class ServerDirectPrintController(http.Controller):
    def _respond_to_printer_request(self, receipt_to_print=None):
        """Send a formatted response as expected by the Epson Server Direct Print protocol.
        If there is no receipt to print an empty response must always be sent with status 200.

        :param receipt_to_print: The receipt content to print or None for any other response.
        :return: A response to be sent back to the Epson printer.
        """
        content_length = len(receipt_to_print) if receipt_to_print else 0
        headers = [
            ('Content-Type', 'text/xml; charset=utf-8'),
            ('Content-Length', content_length),
        ]
        return request.make_response(receipt_to_print, status=200, headers=headers)

    def _print_result_notify_pos(self, pos_config_id, print_result):
        """Notify the POS about the print job result via websocket.

        :param pos_config_id: The POS configuration id to notify about the print job result.
        :param print_result: The print result dictionary containing the print job id and status.
        :return: None
        """
        pos_config = request.env['pos.config'].sudo().browse(int(pos_config_id))
        pos_config and pos_config._notify('EPSON_SERVER_DIRECT_PRINT', print_result)
        _logger.debug("Notified POS %s config id %s about print results: %s", pos_config.name, pos_config.id, print_result)

    def _epson_print_status_response(self, printer_name, response_file, pos_config_id):
        """This method is called when the Epson printer sends a response after printing a receipt.
        It extracts the print result from the XML response and notifies the POS about the print job status.

        :param printer_name: The name of the Epson printer sending the response.
        :param response_file: The XML response file containing the print job status.
        :param pos_config_id: The POS configuration id to notify about the print job status.
        :return: A response to be sent back to the Epson printer with all the job ids and their results in a list.
        """
        _logger.debug("Epson printer %s status response received: %s", printer_name, response_file)
        # Extract print result from the received xml response
        root = ET.fromstring(response_file)
        results = []
        for epos_elem in root.findall(".//ePOSPrint"):
            job_id_elem = epos_elem.find(".//{*}printjobid")
            response_elem = epos_elem.find(".//{*}response")
            if response_elem is not None:
                job_id = job_id_elem.text if job_id_elem is not None else None
                response_attribute = response_elem.attrib
                error_code = response_attribute.get("code")
                results.append({
                    "printJobId": job_id,
                    "success": response_attribute.get("success"),
                    "errorCode": error_code,
                })
        self._print_result_notify_pos(pos_config_id, results)
        return self._respond_to_printer_request()

    def _respond_with_receipt_to_print(self, pos_config_id):
        """This method is called when the Epson printer polls for print jobs.
        It checks if there are any print jobs in the queue and responds with the receipts to print.

        :param pos_config_id: The PoS configuration id identifying a queue.
        :return: A response containing the receipt to print or an empty response if no jobs are available.
        """
        receipt_to_print = None
        config_id = self.env['pos.config'].sudo().browse(int(pos_config_id))
        queued_receipt = config_id.epson_server_pending_receipt_ids

        if len(queued_receipt):
            older_one = queued_receipt[0]
            others = queued_receipt[1:]
            all_match = [re.search(r"<ePOSPrint>.*?</ePOSPrint>", receipt, re.DOTALL) for receipt in others.mapped('receipt')]

            for match in all_match:
                before, sep, after = older_one.receipt.rpartition("</PrintRequestInfo>")
                epos_print_block = match.group(0)
                new_xml = before + epos_print_block + sep + after
                older_one.receipt = new_xml

            receipt_to_print = older_one.receipt
            older_one.unlink()
            others.unlink()

        return self._respond_to_printer_request(receipt_to_print)

    @http.route('/point_of_sale/epson_server_direct_print/<string:pos_config_id>/get_receipt_from_queue', auth="public", type='http', csrf=False)
    def get_receipt_from_queue(self, pos_config_id="", Name=None, ConnectionType=None, ID=None, ResponseFile=None):
        """This controller is polled by the printer to check for available print jobs or to give the print job result
        The printer needs to have its "ID" parameter set to the POS configuration access token.
        Without this the access here will be refused
        Documentation: https://files.support.epson.com/pdf/pos/bulk/tm-int_sdp_um_e_reve.pdf
        Danger zone: this route is public and can be accessed by anyone with the URL.

        :param pos_config_id: The PoS configuration id identifying a queue.
        :param Name: The name of the Epson printer.
        :param ConnectionType: 'GetRequest' to get a print job / 'SetResponse' to send a print job result.
        :param ID: The first 30 characters of the database uuid.
        :param ResponseFile: The XML response file containing the print job status.
        :return: A response to be sent back to the Epson printer.
        """
        # Ensure the request format validity / refuse unauthorized requests
        db_uuid = request.env['ir.config_parameter'].sudo().get_str('database.uuid')
        if not db_uuid or db_uuid[:30].strip() != ID:  # 30 is the max size in printer settings
            _logger.warning("Invalid ID in request data %s %s. Ignoring the request", ConnectionType, ID)
            return self._respond_to_printer_request()
        # 1. The route is called when waiting for a printing job
        if ConnectionType == "GetRequest":
            return self._respond_with_receipt_to_print(pos_config_id)
        # 2. The route is called to notify the print job completion status
        if ConnectionType == "SetResponse" and ResponseFile:
            return self._epson_print_status_response(Name, ResponseFile, pos_config_id)
        # 3. The route is called with invalid data / accessed directly. Reject the request.
        _logger.warning("Epson direct print route called with invalid data: %s %s Ignoring the request.", ConnectionType, ResponseFile)
        return self._respond_to_printer_request()
