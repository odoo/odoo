# -*- coding: utf-8 -*-
from openerp.addons.web import http
from openerp.addons.web.http import request
import base64

from urllib import quote_plus

class website_hr_recruitment(http.Controller):

    @http.route(['/jobs'], type='http', auth="public")
    def career(self, **post):
        website = request.registry['website']
        jobpost_ids = request.registry['hr.job'].search(request.cr, request.uid, [("state", "=", 'open')])
        request.cr.execute("select distinct(com.id) from hr_job job, res_company com where com.id=job.company_id")
        ids = [] 
        for i in request.cr.fetchall():
            ids.append(i[0])
        companies = request.registry['res.company'].browse(request.cr, request.uid, ids)
        values = website.get_rendering_context({
            'companies': companies,
            'res_job': request.registry['hr.job'].browse(request.cr, request.uid, jobpost_ids)
        })
        html = website.render("website_hr_recruitment.jobs", values)
        return html

    @http.route(['/job/detail/<id>'], type='http', auth="public")
    def detail(self, id=0):
        id = id and int(id) or 0
        website = request.registry['website']
        values = website.get_rendering_context({
            'job': request.registry['hr.job'].browse(request.cr, request.uid, id)
        })
        html = website.render("website_hr_recruitment.detail", values)
        return html

    @http.route(['/job/success'], type='http', auth="admin")
    def success(self, **post):
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
        website = request.registry['website']
        values = website.get_rendering_context({
                'jobid': post['job_id']
           })
        html = website.render("website_hr_recruitment.thankyou", values)
        return html
# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
