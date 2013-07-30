# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.controllers.main import template_values
import base64
import tempfile

from urllib import quote_plus

class website_career(http.Controller):

    @http.route(['/career'], type='http', auth="admin")
    def career(self, *arg, **post):
        values = template_values()
        jobpost_ids = request.registry['hr.job'].search(request.cr, request.uid, [("state", "=", 'open')])
        values.update({
           'res_job': request.registry['hr.job'].browse(request.cr, request.uid, jobpost_ids),
           'res_company': request.registry['res.company'].browse(request.cr, request.uid, 1)
        })
        html = request.registry.get("ir.ui.view").render(request.cr, request.uid, "website_career.career", values)
        return html

    @http.route(['/job/detail/<id>'], type='http', auth="admin")
    def detail(self, id=0):
        values = template_values()
        id = id and int(id) or 0
        values.update({
            'job': request.registry['hr.job'].browse(request.cr, request.uid, id),
            'res_company': request.registry['res.company'].browse(request.cr, request.uid, 1)
        })
        html = request.registry.get("ir.ui.view").render(request.cr, request.uid, "website_career.detail", values)
        return html

    @http.route(['/job/success'], type='http', auth="admin")
    def success(self, *arg, **post):
        id = request.registry['hr.applicant'].create(request.cr, request.uid, post)
        if post['ufile']:
            attachment_values = {
                'name': post['ufile'].filename,
                'datas': base64.encodestring(post['ufile'].read()),
                'datas_fname': post['ufile'].filename,
                'res_model': 'hr.applicant',
                'res_name': post['name'],
                'res_id': id
                }
            request.registry['ir.attachment'].create(request.cr, request.uid, attachment_values)
        values = template_values()
        values.update({
               'jobid': post['job_id'],
               'res_company': request.registry['res.company'].browse(request.cr, request.uid, 1)
           })
        html = request.registry.get("ir.ui.view").render(request.cr, request.uid, "website_career.thankyou", values)
        return html
# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
