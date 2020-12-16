# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io

from PyPDF2 import  PdfFileReader, PdfFileWriter
from reportlab.pdfgen import canvas

from odoo import _
from odoo.http import request, route, Controller



class HrFleet(Controller):
    @route(["/fleet/print_claim_report/<int:employee_id>"], type='http', auth='user')
    def get_claim_report_user(self, employee_id, **post):
        if not request.env.user.has_group('fleet.fleet_group_manager'):
            return request.not_found()

        employee = request.env['hr.employee'].search([('id', '=', employee_id)], limit=1)
        partner_ids = (employee.user_id.partner_id | employee.sudo().address_home_id).ids
        if not employee or not partner_ids:
            return request.not_found()

        car_assignation_logs = request.env['fleet.vehicle.assignation.log'].search([('driver_id', 'in', partner_ids)])
        doc_list = request.env['ir.attachment'].search([
            ('res_model', '=', 'fleet.vehicle.assignation.log'),
            ('res_id', 'in', car_assignation_logs.ids)], order='create_date')

        writer = PdfFileWriter()

        font = "Helvetica"
        normal_font_size = 14

        for document in doc_list:
            car_line_doc = request.env['fleet.vehicle.assignation.log'].browse(document.res_id)
            try:
                reader = PdfFileReader(io.BytesIO(base64.b64decode(document.datas)), strict=False, overwriteWarnings=False)
            except Exception:
                continue

            width = float(reader.getPage(0).mediaBox.getUpperRight_x())
            height = float(reader.getPage(0).mediaBox.getUpperRight_y())

            header = io.BytesIO()
            can = canvas.Canvas(header)
            can.setFont(font, normal_font_size)
            can.setFillColorRGB(1, 0, 0)

            car_name = car_line_doc.vehicle_id.display_name
            date_start = car_line_doc.date_start
            date_end = car_line_doc.date_end or '...'

            text_to_print = _(
                "%(car_name)s (driven from: %(date_start)s to %(date_end)s)",
                car_name=car_name,
                date_start=date_start,
                date_end=date_end
            )
            can.drawCentredString(width / 2, height - normal_font_size, text_to_print)
            can.save()
            header_pdf = PdfFileReader(header, overwriteWarnings=False)

            for page_number in range(0, reader.getNumPages()):
                page = reader.getPage(page_number)
                page.mergePage(header_pdf.getPage(0))
                writer.addPage(page)

        _buffer = io.BytesIO()
        writer.write(_buffer)
        merged_pdf = _buffer.getvalue()
        _buffer.close()

        pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(merged_pdf))]

        return request.make_response(merged_pdf, headers=pdfhttpheaders)
