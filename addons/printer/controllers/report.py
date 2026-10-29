# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import Controller, request, route


class PrinterReportController(Controller):

    @route('/printer/report_documents', type='jsonrpc', auth='user')
    def report_documents(self, report_name, printer_ids, res_ids=None, data=None, context=None):
        """ Render a report for printers.

        :return: the documents to send to each kind of printer, see
            ``ir.actions.report._render_printer_documents``
        """
        if context:
            request.update_context(**context)
        printers = request.env['printer.printer'].browse(printer_ids).exists()
        return request.env['ir.actions.report']._render_printer_documents(
            report_name, printers, res_ids or [], data=data,
        )
