# -*- coding: utf-8 -*-
import base64
from odoo import http
from odoo.http import request

class delivery_printlabel(http.Controller):
    @http.route([
        "/delivery/printlabel/<model('ir.attachment'):attachment>"], type='http', auth='user')
    def print_label(self, attachment):
        pdf = base64.decodestring(attachment.datas)
        pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
        return request.make_response(pdf, headers=pdfhttpheaders)        
