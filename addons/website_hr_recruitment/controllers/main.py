# -*- coding: utf-8 -*-
from openerp.addons.web import http
from openerp import SUPERUSER_ID
from openerp.addons.web.http import request
from openerp.addons.website import website
import base64
import simplejson

from urllib import quote_plus

class website_hr_recruitment(http.Controller):

    @website.route(['/jobs', '/jobs/page/<int:page>/', '/department/<id>/', '/department/<id>/page/<int:page>/'], type='http', auth="public")
    def jobs(self, id=0, page=1, **post):
        id = id and int(id) or 0
        website = request.registry['website']
        hr_job_obj = request.registry['hr.job']
        hr_department_obj = request.registry['hr.department']

        domain = [(1, '=', 1)] or [('website_published', '=', True)]
        search = [("state", 'in', ['recruit', 'open'])]
        domain += search

        jobpost_ids = hr_job_obj.search(request.cr, request.uid, domain)
        request.cr.execute("select distinct(com.id) from hr_job job, res_company com where com.id=job.company_id")
        ids = []
        for i in request.cr.fetchall():
            ids.append(i[0])
        companies = request.registry['res.company'].browse(request.cr, request.uid, ids)
        vals = {}
        for rec in hr_job_obj.browse(request.cr, request.uid, jobpost_ids):
            vals[rec.id] = {'count': int(rec.no_of_recruitment), 'date_recruitment': rec.write_date.split(' ')[0]}
        step = 5
        pager = request.website.pager(url="/jobs/", total=len(jobpost_ids), page=page, step=step, scope=5)
        jobpost_ids = hr_job_obj.search(request.cr, request.uid, domain, limit=step, offset=pager['offset'])
        department_ids = []
        request.cr.execute("select * from hr_department")
        for i in request.cr.fetchall():
            department_ids.append(i[0])
        if not id:
            id = 1
        active = id
        jobids = hr_job_obj.search(request.cr, request.uid, [('department_id','=',id)])
        step = 5
        pager = request.website.pager(url="/jobs/", total=len(jobids), page=page, step=step, scope=5)
        values = {
            'active': active,
            'companies': companies,
            'res_job': hr_job_obj.browse(request.cr, request.uid, jobids),
#            'res_job': hr_job_obj.browse(request.cr, request.uid, jobpost_ids),
            'departments': hr_department_obj.browse(request.cr, request.uid, department_ids),
            'vals': vals,
            'no_of_jobs': len(hr_job_obj.browse(request.cr, request.uid, jobpost_ids)),
            'pager': pager
        }
        return request.website.render("website_hr_recruitment.index", values)


    @website.route(['/job/detail/<id>'], type='http', auth="public")
    def detail(self, id=0):
        id = id and int(id) or 0
        website = request.registry['website']
        values = {
            'job': request.registry['hr.job'].browse(request.cr, request.uid, id),
            'vals_date': request.registry['hr.job'].browse(request.cr, request.uid, id).write_date.split(' ')[0]
        }
        return request.website.render("website_hr_recruitment.detail", values)

    @website.route(['/job/success'], type='http', auth="admin")
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
        values = {
                'jobid': post['job_id']
           }
        return request.website.render("website_hr_recruitment.thankyou", values)

    @website.route(['/job/detail/<int:job_id>/subscribe'], type='http', auth="public")
    def subscribe(self, event_id=None, **post):
        partner_obj = request.registry['res.partner']
        job_obj = request.registry['hr.job']
        user_obj = request.registry['res.users']

        if job_id and 'subscribe' in post and (post.get('email') or not request.context['is_public_user']):
            if request.context['is_public_user']:
                partner_ids = partner_obj.search(
                    request.cr, SUPERUSER_ID, [("email", "=", post.get('email'))],
                    context=request.context)
                if not partner_ids:
                    partner_data = {
                        "email": post.get('email'),
                        "name": "Subscribe: %s" % post.get('email')
                    }
                    partner_ids = [partner_obj.create(
                        request.cr, SUPERUSER_ID, partner_data, context=request.context)]
            else:
                partner_ids = [user_obj.browse(
                    request.cr, request.uid, request.uid,
                    context=request.context).partner_id.id]
            job_obj.check_access_rule(request.cr, request.uid, [event_id],
                                        'read', request.context)
            job_obj.message_subscribe(request.cr, SUPERUSER_ID, [event_id],
                                        partner_ids, request.context)

        return self.detail(job_id=job_id)

    @website.route(['/job/detail/<int:job_id>/unsubscribe'], type='http', auth="public")
    def unsubscribe(self, job_id=None, **post):
        partner_obj = request.registry['res.partner']
        job_obj = request.registry['hr.job']
        user_obj = request.registry['res.users']

        if job_id and 'unsubscribe' in post and (post.get('email') or not request.context['is_public_user']):
            if request.context['is_public_user']:
                partner_ids = partner_obj.search(
                    request.cr, SUPERUSER_ID, [("email", "=", post.get('email'))],
                    context=request.context)
            else:
                partner_ids = [user_obj.browse(request.cr, request.uid, request.uid, request.context).partner_id.id]
            job_obj.check_access_rule(request.cr, request.uid, [event_id], 'read', request.context)
            job_obj.message_unsubscribe(request.cr, SUPERUSER_ID, [job_id], partner_ids, request.context)

        return self.detail(job_id=job_id)

    @website.route('/recruitment/published', type='json', auth="admin")
    def published (self, **post):
        hr_job = request.registry['hr.job']
        id = int(post['id'])
        rec = hr_job.browse(request.cr, request.uid, id)
        vals = {}

        if rec.website_published:
            vals['state'] = 'recruit'
            if rec.no_of_recruitment == 0.0:
                vals ['no_of_recruitment'] = 1.0
        else:
            vals['state'] = 'open'
            vals ['no_of_recruitment'] = 0.0

        res = hr_job.write(request.cr, request.uid, [rec.id], vals)
        obj = hr_job.browse(request.cr, request.uid, id)
        return { 'count': obj.no_of_recruitment, 'state': obj.state, 'published': obj.website_published }
# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
