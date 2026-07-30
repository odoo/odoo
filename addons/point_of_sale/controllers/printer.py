import logging
import re
from xml.etree import ElementTree as ET

from odoo import http
from odoo.tools import consteq

from odoo.addons.point_of_sale.models.pos_printer import PosPrinter

_logger = logging.getLogger(__name__)


def _make_response(receipt=None) -> http.Response:
    """Send a formatted response as expected by the Epson Server Direct Print protocol.
    If there is no receipt to print an empty response must always be sent with status 200.

    :param receipt: The receipt content to print or None for any other response.
    :return: A response to be sent back to the Epson printer.
    """
    content_length = len(receipt) if receipt else 0
    return http.request.make_response(
        receipt,
        status=200,
        headers=[
            ("Content-Type", "text/xml; charset=utf-8"),
            ("Content-Length", str(content_length)),
        ],
    )


def _get_jobs(printer_id: PosPrinter) -> http.Response:
    """Printer polls for print jobs.
    Checks if there are any print jobs in the queue and responds with the receipts to print.

    :param printer_id: The PoS configuration id identifying a queue.
    :return: receipt to print or empty if no job available.
    """
    queued_receipt = printer_id.queued_receipt_ids
    if not len(queued_receipt):
        return _make_response()

    older = queued_receipt[0]
    others = queued_receipt[1:]
    receipts = [
        re.search(r"<ePOSPrint>.*?</ePOSPrint>", receipt, re.DOTALL)
        for receipt in others.mapped('receipt')
    ]

    before, sep, after = older.receipt.rpartition("</PrintRequestInfo>")
    print_block = "".join(receipt.group(0) for receipt in receipts)
    receipt_to_print = before + print_block + sep + after

    older.unlink()
    others.unlink()
    return _make_response(receipt_to_print)


def _notify_pos(printer_id: PosPrinter, result: list):
    """Notify the POS about the print job result via websocket.

    :param printer_id: The POS Printer id to notify about the print job result.
    :param result: The print result dictionary containing the print job id and status.
    """
    config_ids = printer_id.env["pos.config"].sudo().search([
        "|", ("preparation_printer_ids", "in", printer_id.id), ("receipt_printer_ids", "in", printer_id.id),
    ])
    config_ids and config_ids._notify("POLLING_PRINTER", result)


def _response_webhook(response_file: str, printer_id: PosPrinter) -> http.Response:
    """Printer sends a response after printing a receipt.
    Extracts print result from XML response and notifies the POS about the print job status.

    :param printer_name: Name of the printer sending the response.
    :param response_file: XML response file containing job status.
    :param printer_id: POS Printer id to notify about the print job status.
    :return: response to be sent to the printer with all the job ids and their results in a list.
    """
    # Extract print result from the received XML response
    results = []
    for epos_elem in ET.fromstring(response_file).findall(".//ePOSPrint"):
        job_id_elem = epos_elem.find(".//{*}printjobid")
        response_elem = epos_elem.find(".//{*}response")
        if response_elem is not None:
            job_id = job_id_elem.text if job_id_elem is not None else None
            results.append({
                "printJobId": job_id,
                "success": response_elem.attrib.get("success"),
                "errorCode": response_elem.attrib.get("code"),
            })
    _notify_pos(printer_id, results)
    return _make_response()


class Printer(http.Controller):
    @http.route(
        "/pos/printer/polling/<int:printer_id>/<string:token>/get_print_jobs", auth="public", type='http', csrf=False
    )
    def get_print_jobs(
        self,
        printer_id: int,
        token: str,
        ConnectionType: str = "",
        ResponseFile: str = "",
    ) -> http.Response:
        """Polled by the printer to:
        - check for available jobs,
        - give the print job result

        Documentation: https://files.support.epson.com/pdf/pos/bulk/tm-int_sdp_um_e_reve.pdf
        Danger zone: this route is public and can be accessed by anyone with the URL.

        :param printer_id: PoS Printer id
        :param token: first 30 characters of the database uuid
        :param ConnectionType: `GetRequest` to get a print job / `SetResponse` to send a print job result.
        :param ResponseFile: XML response file containing the print job status.
        :return: Response to be sent back to the Epson printer.
        """
        db_uuid = http.request.env['ir.config_parameter'].sudo().get_str('database.uuid')
        printer_id: PosPrinter = http.request.env["pos.printer"].sudo().browse(printer_id)
        if (
            not db_uuid
            or not consteq(db_uuid[:30].strip(), token)  # 30 is the max size in printer settings
            or printer_id.printer_type != "polling"
        ):
            _logger.warning("Invalid token/id in request data %s. Ignoring the request", ConnectionType)
            return _make_response()

        if ConnectionType == "GetRequest":
            return _get_jobs(printer_id)
        if ConnectionType == "SetResponse" and ResponseFile:
            return _response_webhook(ResponseFile, printer_id)

        _logger.warning(
            "Printer Polling route called with invalid data: %s, %s Ignoring.", ConnectionType, ResponseFile,
        )
        return self._make_response()
