# -*- coding: utf-8 -*-
from openerp.addons.web import http
from openerp import SUPERUSER_ID
from openerp.addons.web.http import request
import base64
import simplejson

from urllib import quote_plus

class website_hr_recruitment(http.Controller):

    @http.route(['/jobs'], type='http', auth="public")
    def jobs(self, **post):
        website = request.registry['website']
        hr_job_obj = request.registry['hr.job']

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
        values = website.get_rendering_context({
            'companies': companies,
            'res_job': hr_job_obj.browse(request.cr, request.uid, jobpost_ids),
            'vals': vals,
            'no_of_jobs': len(hr_job_obj.browse(request.cr, request.uid, jobpost_ids)),
        })
        return website.render("website_hr_recruitment.index", values)

    @http.route(['/job/detail/<id>'], type='http', auth="public")
    def detail(self, id=0):
        id = id and int(id) or 0
        website = request.registry['website']
        values = website.get_rendering_context({
            'job': request.registry['hr.job'].browse(request.cr, request.uid, id)
        })
        return website.render("website_hr_recruitment.detail", values)

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
        return website.render("website_hr_recruitment.thankyou", values)

    @http.route('/recruitment/message_get_subscribed', type='json', auth="admin")
    def message_get_subscribed(self, email, id):
        id = int(id)
        hr_job = request.registry['hr.job']
        partner_obj = request.registry['res.partner']
        partner_ids = partner_obj.search(request.cr, SUPERUSER_ID, [("email", "=", email)])
        if not partner_ids:
            partner_ids = [partner_obj.create(request.cr, SUPERUSER_ID, {"email": email, "name": "Subscribe: %s" % email})]
        hr_job.write(request.cr, request.uid, [id], {'message_follower_ids': partner_ids})
        return 1

    @http.route('/recruitment/message_get_unsubscribed', type='json', auth="admin")
    def message_get_unsubscribed(self, email, id):
        hr_job = request.registry['hr.job']
        id = int(id)
        partner_obj = request.registry['res.partner']
        partner_ids = partner_obj.search(request.cr, SUPERUSER_ID, [("email", "=", email)])
        hr_job.write(request.cr, request.uid, [id], {'message_follower_ids': [(3, pid) for pid in partner_ids]})
        return 1

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
