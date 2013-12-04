# -*- coding: utf-8 -*-
from openerp.addons.web import http
from openerp.tools.translate import _
from openerp.addons.web.http import request
from openerp.addons.website.models import website
from openerp.addons.website.controllers.main import Website as controllers
controllers = controllers()

import base64


class website_hr_recruitment(http.Controller):
    @website.route([
        '/jobs',
        '/jobs/department/<model("hr.department"):department>/office/<model("res.partner"):office>',
        '/jobs/department/<model("hr.department"):department>',
        '/jobs/office/<model("res.partner"):office>'
        ], type='http', auth="public", multilang=True)
    def jobs(self, department=None, office=None):
        jobs = self._browse_jobs([])

        departments = set()
        offices = set()
        for job in jobs:
            if job.department_id:
                departments.add(job.department_id)
            if job.address_id:
                offices.add(job.address_id)

        if department or office:
            domain = []
            if department:
                domain.append(('department_id','=', department.id))
            if office:
                domain.append(('address_id','=', office.id))
            jobs = self._browse_jobs(domain)

        return request.website.render("website_hr_recruitment.index", {
            'jobs': jobs,
            'departments': departments,
            'offices': offices,
            'active': department and department.id or None,
            'office': office and office.id or None
        })

    @website.route(['/job/detail/<model("hr.job"):job>'], type='http', auth="public", multilang=True)
    def detail(self, job, **kwargs):
        return request.website.render("website_hr_recruitment.detail", {'job': job})

    @website.route(['/job/success'], methods=['POST'], type='http', auth="admin", multilang=True)
    def success(self, **post):
        data = {
            'name': _('Online Form'),
            'phone': post.get('phone', False),
            'email_from': post.get('email_from', False),
            'partner_name': post.get('partner_name', False),
            'description': post.get('description', False),
            'department_id': post.get('department_id', False),
            'job_id': post.get('job_id', False),
            'user_id': False
        }

        imd = request.registry['ir.model.data']
        try:
            model, source_id = imd.get_object_reference(request.cr, request.uid, 'hr_recruitment', 'source_website_company')
            data['source_id'] = source_id
        except ValueError:
            pass

        jobid = request.registry['hr.applicant'].create(request.cr, request.uid, data, context=request.context)
        if post['ufile']:
            attachment_values = {
                'name': post['ufile'].filename,
                'datas': base64.encodestring(post['ufile'].read()),
                'datas_fname': post['ufile'].filename,
                'res_model': 'hr.applicant',
                'res_name': data['partner_name'],
                'res_id': jobid
                }
            request.registry['ir.attachment'].create(request.cr, request.uid, attachment_values, context=request.context)
        return request.website.render("website_hr_recruitment.thankyou", {})

    @website.route(['/job/apply'], type='http', auth="public", multilang=True)
    def applyjobpost(self, job):
        [job_object] = request.registry['hr.job'].browse(
            request.cr, request.uid, [int(job)], context=request.context)

        return request.website.render("website_hr_recruitment.applyjobpost", {
            'job': job_object
        })

    @website.route('/job/add_job_offer/', type='http', auth="user", multilang=True, methods=['POST'])
    def add_job_offer(self, **kwargs):
        Job = request.registry.get('hr.job')
        job_id = Job.create(request.cr, request.uid, {
            'name': 'New Job Offer',
        }, context=request.context)

        return request.redirect("/job/detail/%s/?enable_editor=1" % job_id)

    def _browse_jobs(self, domain):
        Jobs = request.registry['hr.job']
        jobpost_ids = Jobs.search(request.cr, request.uid, domain,
            order="website_published desc,no_of_recruitment desc",
            context=request.context)
        jobs = Jobs.browse(request.cr, request.uid, jobpost_ids, context=request.context)
        return jobs
