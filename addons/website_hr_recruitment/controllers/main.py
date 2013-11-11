# -*- coding: utf-8 -*-
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models import website
from openerp.addons.website.controllers.main import Website as controllers
controllers = controllers()

import base64


class website_hr_recruitment(http.Controller):

    @website.route(['/jobs', '/jobs/page/<int:page>/', '/department/<id>/', '/department/<id>/page/<int:page>/'], type='http', auth="public", multilang=True)
    def jobs(self, id=0, page=1):
        id = id and int(id) or 0
        hr_job_obj = request.registry['hr.job']
        hr_department_obj = request.registry['hr.department']

        domain = [("state", 'in', ['recruit', 'open'])]
        if id != 0:
            domain += [('department_id','=', id)]
        jobpost_ids = hr_job_obj.search(request.cr, request.uid, domain)
        request.cr.execute("SELECT DISTINCT(hr_job.company_id) FROM hr_job WHERE hr_job.company_id IS NOT NULL")
        ids = []
        for i in request.cr.fetchall():
            ids.append(i[0])
        companies = request.registry['res.company'].browse(request.cr, request.uid, ids)

        vals = {}
        for rec in hr_job_obj.browse(request.cr, request.uid, jobpost_ids):
            vals[rec.id] = {'count': int(rec.no_of_recruitment), 'date_recruitment': rec.write_date.split(' ')[0]}

        department_ids = []
        request.cr.execute("SELECT * FROM hr_department")
        for i in request.cr.fetchall():
            department_ids.append(i[0])
        active = id

        step = 10
        pager = request.website.pager(url="/jobs/", total=len(jobpost_ids), page=page, step=step, scope=5)
        jobpost_ids = hr_job_obj.search(request.cr, request.uid, domain, limit=step, offset=pager['offset'])

        values = {
            'active': active,
            'companies': companies,
            'res_job': hr_job_obj.browse(request.cr, request.uid, jobpost_ids),
            'departments': hr_department_obj.browse(request.cr, request.uid, department_ids),
            'vals': vals,
            'pager': pager
        }
        return request.website.render("website_hr_recruitment.index", values)

    @website.route(['/job/detail/<model("hr.job"):job>'], type='http', auth="public", multilang=True)
    def detail(self, job):
        values = {
            'job': job,
            'vals_date': job.write_date.split(' ')[0],
        }
        return request.website.render("website_hr_recruitment.detail", values)

    @website.route(['/job/success'], type='http', auth="admin", multilang=True)
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
        values = {
                'jobid': post['job_id']
           }
        return request.website.render("website_hr_recruitment.thankyou", values)

    @website.route(['/apply/<model("hr.job"):job>'], type='http', auth="public", multilang=True)
    def applyjobpost(self, job):
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
# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
