# -*- coding: utf-8 -*-
from openerp.addons.web import http
from openerp.tools.translate import _
from openerp.addons.web.http import request
from openerp.addons.website.models import website
from openerp.addons.website.controllers.main import Website as controllers
controllers = controllers()

import base64


class website_hr_recruitment(http.Controller):

    @website.route(['/jobs', '/department/<model("hr.department"):id>'], type='http', auth="public", multilang=True)
    def jobs(self, department=None, page=0):
        hr_job_obj = request.registry['hr.job']
        domain = []
        if department:
            domain += [('department_id','=', department.id)]
        jobpost_ids = hr_job_obj.search(request.cr, request.uid, domain, order="website_published,no_of_recruitment", context=request.context)
        return request.website.render("website_hr_recruitment.index", {
            'jobs': hr_job_obj.browse(request.cr, request.uid, jobpost_ids, request.context),
        })

    @website.route(['/job/detail/<model("hr.job"):job>'], type='http', auth="public", multilang=True)
    def detail(self, job):
        values = {
            'job': job,
            'vals_date': job.write_date.split(' ')[0],
        }
        return request.website.render("website_hr_recruitment.detail", values)

    @website.route(['/job/success'], type='http', auth="admin", multilang=True)
    def success(self, **post):
        data = {
            'name': _('Online Form'),
            'phone': post.get('phone', False),
            'email_from': post.get('email_from', False),
            'partner_name': post.get('partner_name', False),
            'description': post.get('description', False),
            'department_id': post.get('department_id', False),
            'job_id': post.get('job_id', False)
        }

        imd = request.registry['ir.model.data']
        try:
            model, source_id = imd.get_object_reference(request.cr, request.uid, 'hr_recruitment', 'source_website_company')
            data['source_id'] = source_id
        except ValueError, e:
            pass

        jobid = request.registry['hr.applicant'].create(request.cr, request.uid, data, context=request.context)
        if post['ufile']:
            attachment_values = {
                'name': post['ufile'].filename,
                'datas': base64.encodestring(post['ufile'].read()),
                'datas_fname': post['ufile'].filename,
                'res_model': 'hr.applicant',
                'res_name': post['name'],
                'res_id': jobid
                }
            request.registry['ir.attachment'].create(request.cr, request.uid, attachment_values, context=request.context)
        return request.website.render("website_hr_recruitment.thankyou", {})

    @website.route(['/job/apply', '/job/apply/<model("hr.job"):job>'], type='http', auth="public", multilang=True)
    def applyjobpost(self, job=None):
        return request.website.render("website_hr_recruitment.applyjobpost", { 'job': job })

    @website.route('/job/publish', type='json', auth="admin", multilang=True)
    def publish (self, id, object):
        res = controllers.publish(id, object)

        hr_job = request.registry[object]
        id = int(id)
        rec = hr_job.browse(request.cr, request.uid, id)
        vals = {}
        if rec.website_published:
            vals['state'] = 'recruit'
            if not rec.no_of_recruitment:
                vals ['no_of_recruitment'] = 1.0
        else:
            vals['state'] = 'open'
        hr_job.write(request.cr, request.uid, [rec.id], vals, context=request.context)

        return res
