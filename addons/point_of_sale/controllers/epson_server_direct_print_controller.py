import queue
import logging
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

class ServerPrintController(http.Controller):
    def __init__(self):
        super().__init__()
        self.receipt_jobs_queues = {}

    @http.route('/point_of_sale/epson_server_direct_print/<string:pos_config_access_token>/add_receipt_to_print_queue', auth="user", type='jsonrpc')
    def add_receipt_to_print_queue(self, pos_config_access_token, job_id, receipt_to_print):
        """
        This controller is called by the POS to add a receipt to the print queue.
        :param pos_config_access_token: The POS configuration access token to identify the print queue.
        :param job_id: The unique job id for the print job.
        :param receipt_to_print: The receipt content to print.
        :return: A dictionary with the status of the operation.
        """
        receipts_queue = self.receipt_jobs_queues.get(pos_config_access_token)
        # Create print queue if it doesn't exist
        if not receipts_queue:
            receipts_queue = queue.Queue(maxsize=50)  # FIFO
            receipts_queue.printer_active = False  # Custom attribute to track if a printer is associated to this queue
            self.receipt_jobs_queues[pos_config_access_token] = receipts_queue
        # If the queue exists but hasn't been polled by any printer yet avoid adding new jobs
        if not receipts_queue.printer_active:
            _logger.warning("No printer configured for pos config with access token %s, cannot add new job id %s receipt to print queue", pos_config_access_token, job_id)
            return {'errorCode': 'ERROR_CODE_PRINTER_INACTIVE'}
        # Add receipt to print queue
        try:
            receipts_queue.put({
                'receipt': receipt_to_print,
                'job_id': job_id,
            }, timeout=3)
        except queue.Full:
            # Corner case where receipt queue is full and noone is polling, reset the queue to avoid user getting stuck
            _logger.warning("Queue for POS config with access token %s is full, cannot add new job id %s receipt to print queue, resetting queue.", pos_config_access_token, job_id)
            self.receipt_jobs_queues[pos_config_access_token] = None
            receipts_queue.printer_active = False
            return {'errorCode': 'ERROR_CODE_PRINT_QUEUE_FULL'}
        _logger.info("Added receipt with job id %s to the pos config with access token %s", job_id, pos_config_access_token)
        return {'status': 'success', 'message': f'Receipt with job_id {job_id} added to print queue for POS config with access token {pos_config_access_token}'}

    def _respond_to_printer_request(self, receipt_to_print=None):
        """
        Send a formatted response as expected by the Epson Server Direct Print protocol.
        If there is no receipt to print an empty response must always sent with status 200.
        :param receipt_to_print: The receipt content to print or None for any other response.
        :return: A response to be sent back to the Epson printer.
        """
        if (receipt_to_print):
            _logger.info("Sending receipt to Epson printer: %s", receipt_to_print)
        content_length = len(receipt_to_print) if receipt_to_print else 0
        headers = [
            ('Content-Type', 'text/xml; charset=utf-8'),
            ('Content-Length', content_length),
        ]
        return request.make_response(receipt_to_print, status=200, headers=headers)

    def _print_result_notify_pos(self, pos_config_access_token, print_result):
        """
        Notify the POS about the print job result via websocket.
        :param pos_config_access_token: The POS configuration access token to notify about the print job result.
        :param print_result: The print result dictionary containing the print job id and status.
        :return: None
        """
        pos_config = request.env['pos.config'].sudo().search([('access_token', '=', pos_config_access_token)], limit=1)
        if pos_config:
            pos_config.notify_epson_server_direct_print_result(print_result)
            _logger.info("Notified POS %s config id %s about print job id %s result: %s", pos_config.name, pos_config.id, print_result.get('printJobId'), print_result)
        else:
            _logger.warning("Pos config with access token %s not found, cannot notify about print job result %s", pos_config_access_token, print_result)

    def _epson_print_status_response(self, printer_request_params, pos_config_access_token):
        """
        This method is called when the Epson printer sends a response after printing a receipt.
        It extracts the print result from the XML response and notifies the POS about the print job status.
        :param printer_request_params: The parameters received from the Epson printer.
        :param pos_config_access_token: The POS configuration access token to notify about the print job status.
        :return: A response to be sent back to the Epson printer.
        """
        printer_name = printer_request_params.get('Name', 'Epson Server Direct')
        # Extract print result from the received xml response
        root = ET.fromstring(printer_request_params['ResponseFile'])
        # Extract print job id
        print_job_id_elem = root.find('.//{*}printjobid')
        print_job_id = None
        if print_job_id_elem is not None:
            print_job_id = print_job_id_elem.text
            if not print_job_id:
                _logger.warning("%s printer job confirmation does not contain a print job id, the printer needs a firmware update", printer_name)
        response_elem = root.find('.//{*}response')
        # If wrong receipt format / message is sent to the printer, response_elem will be None
        if response_elem is None:
            _logger.error("%s printer responded to a bad receipt format %s", printer_name, printer_request_params)
        else:
            reponse_attr = response_elem.attrib
            # Printing failed
            if reponse_attr.get('success') != 'true':
                error_code = reponse_attr.get('code')
                error_message = EPSON_ERRORS.get(error_code, 'Unknown error message')
                _logger.warning("%s printer response indicates an error %s: %s", printer_name, error_code, error_message)
                self._print_result_notify_pos(pos_config_access_token, {'printJobId': print_job_id, 'success': 'false', 'errorCode': error_code})
            # Printing was successful
            else:
                _logger.info("Epson server direct printer response indicates a successful print job id %s", print_job_id)
                self._print_result_notify_pos(pos_config_access_token, {'printJobId': print_job_id, 'success': 'true', 'errorCode': None})
        return self._respond_to_printer_request()

    def _respond_with_receipt_to_print(self, printer_request_params, pos_config_access_token):
        """
        This method is called when the Epson printer polls for print jobs.
        It checks if there are any print jobs in the queue and responds with the receipt to print.
        :param printer_request_params: The parameters received from the Epson printer.
        :param pos_config_id: The POS configuration ID to check for print jobs.
        :return: A response containing the receipt to print or an empty response if no jobs are available.
        """
        receipts_queue = self.receipt_jobs_queues.get(pos_config_access_token)
        if receipts_queue:
            receipts_queue.printer_active = True  # Notify the queue that a printer is associated to it and is active
            try:
                queued_receipt = receipts_queue.get(timeout=3)
                if queued_receipt:
                    _logger.info("Printer %s is printing job id %s", printer_request_params.get('Name', 'Epson Server Direct'), queued_receipt['job_id'])
                    return self._respond_to_printer_request(queued_receipt['receipt'])
            except queue.Empty:
                _logger.debug("Receipt queue for pos config with access token %s is empty, returning empty response to printer", pos_config_access_token)
        return self._respond_to_printer_request()

    @http.route('/point_of_sale/epson_server_direct_print/<string:pos_config_access_token>/poll_server_print', auth="public", type='http', csrf=False)
    def poll_server_print(self, pos_config_access_token=""):
        """
        This controller is polled by the Epson printer to check for available print jobs
        It is also called by the printer to notify the print job completion status or printing errors
        Documentation: https://files.support.epson.com/pdf/pos/bulk/tm-int_sdp_um_e_reve.pdf
        Danger zone: this route is public and can be accessed by anyone with the URL.
        """
        request_params = request.params
        _logger.debug("Epson direct print queue controller called with params: %s", request_params)
        # 1. The route is called to notify the print job completion status ('ConnectionType': 'SetResponse')
        if request_params.get('ConnectionType') == "SetResponse" and "ResponseFile" in request_params:
            return self._epson_print_status_response(request_params, pos_config_access_token)
        # 2. The route is called when waiting for a printing job ('ConnectionType': 'GetRequest')
        if request_params.get('ConnectionType') == "GetRequest":
            return self._respond_with_receipt_to_print(request_params, pos_config_access_token)
        # 3. The route is called with invalid data / accessed directly. Reject the request.
        _logger.warning("Epson direct print route called with invalid data: %s. Ignoring the request.", request_params)
        return self._respond_to_printer_request()
