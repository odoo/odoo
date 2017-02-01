# -*- coding: utf-8 -*-
from datetime import datetime
import json
import logging

import werkzeug.utils

from odoo import http
from odoo.addons.base.ir.ir_mail_server import MailDeliveryException
from odoo.http import request

_logger = logging.getLogger(__name__)


class PosController(http.Controller):

    @http.route('/pos/web', type='http', auth='user')
    def pos_web(self, debug=False, **k):
        # if user not logged in, log him in
        pos_sessions = request.env['pos.session'].search([('state', '=', 'opened'), ('user_id', '=', request.session.uid)])
        if not pos_sessions:
            return werkzeug.utils.redirect('/web#action=point_of_sale.action_client_pos_menu')
        pos_sessions.login()
        context = {
            'session_info': json.dumps(request.env['ir.http'].session_info())
        }
        return request.render('point_of_sale.index', qcontext=context)

    @http.route('/pos/sale_details_report', type='http', auth='user')
    def print_sale_details(self, date_start=False, date_stop=False, **kw):
        r = request.env['report.point_of_sale.report_saledetails']
        pdf = request.env['report'].with_context(date_start=date_start, date_stop=date_stop).get_pdf(r, 'point_of_sale.report_saledetails')
        pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
        return request.make_response(pdf, headers=pdfhttpheaders)

    @http.route('/pos/debugging_mail', type='json', auth="user")
    def send_email(self, debug_type, date_string=None, data=None, **kwargs):
        Mail_mail = request.env['mail.mail']
        Ir_attachment = request.env['ir.attachment']
        user_from = request.env['res.users'].browse(request.session.uid)

        if not date_string:
            date_string = json.loads(data).keys()[0] + "_" + datetime.now().strftime("%Y-%m-%d_%H_%M_%S")

        subject = "[Odoo][DEBUG] Support " + date_string

        mail_to_send = None
        try:
            mail_body = ("<p>Hello,</p>" +
                         "<p>Please find in attachment the export of debug type [" + debug_type + "]</p>" +
                         "<p>Best Regards</p>")

            mail_to_send = Mail_mail.create({
                'subject': subject,
                'body_html': mail_body,
                'email_to': user_from.email,
                "email_from": user_from.email})

            attachement = Ir_attachment.create({
                'name': subject,
                'datas_fname': date_string + '.txt',
                'datas': str(data).encode('base64'),
                'res_model': 'mail.mail',
                'res_id': mail_to_send.id})

            mail_to_send.write({'attachment_ids': [(6, 0, [attachement.id])]
                                })

            mail_to_send.send()

            _logger.info("Email Sent")
            return {'status': "Success",
                    'message': "E-Mail sent to " + user_from.email}

        except MailDeliveryException as mde:
            return {'status': 'Failed',
                    'message': "Exception: " + str(mde)}

        except Exception as e:
            return {'status': 'Error',
                    'message': "Exception: " + str(e)}
