# -*- coding: utf-8 -*-
from openerp.addons.web import http
from openerp import SUPERUSER_ID
from openerp.addons.web.http import request
from openerp.addons.website import website
import base64
import simplejson

from urllib import quote_plus

class website_hr_recruitment(http.Controller):

    @website.route(['/jobs'], type='http', auth="public")
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
        values = {
            'companies': companies,
            'res_job': hr_job_obj.browse(request.cr, request.uid, jobpost_ids),
            'vals': vals,
            'no_of_jobs': len(hr_job_obj.browse(request.cr, request.uid, jobpost_ids)),
        }
        return request.webcontext.render("website_hr_recruitment.index", values)

    @website.route(['/job/detail/<id>'], type='http', auth="public")
    def detail(self, id=0):
        id = id and int(id) or 0
        website = request.registry['website']
        values = {
            'job': request.registry['hr.job'].browse(request.cr, request.uid, id)
        }
        return request.webcontext.render("website_hr_recruitment.detail", values)

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
        return request.webcontext.render("website_hr_recruitment.thankyou", values)

    @website.route('/recruitment/message_get_subscribed', type='json', auth="admin")
    def message_get_subscribed(self, email, id, mail_group_id):
        id = int(id)
        mail_group_id = int(mail_group_id)
        group_obj = request.registry['mail.group']
        partner_obj = request.registry['res.partner']
        partner_ids = partner_obj.search(request.cr, SUPERUSER_ID, [("email", "=", email)])
        if not partner_ids:
            partner_ids = [partner_obj.create(request.cr, SUPERUSER_ID, {"email": email, "name": "Subscribe: %s" % email})]
        group_obj.check_access_rule(request.cr, request.uid, [mail_group_id], 'read')
        group_obj.message_subscribe(request.cr, SUPERUSER_ID, [mail_group_id], partner_ids)
        return 1

    @website.route('/recruitment/message_get_unsubscribed', type='json', auth="admin")
    def message_get_unsubscribed(self, email, id, mail_group_id):
        mail_group_id = int(mail_group_id)
        id = int(id)
        partner_obj = request.registry['res.partner']
        group_obj = request.registry['mail.group']
        partner_ids = partner_obj.search(request.cr, SUPERUSER_ID, [("email", "=", email)])
        group_obj.check_access_rule(request.cr, request.uid, [mail_group_id], 'read')
        group_obj.message_unsubscribe(request.cr, SUPERUSER_ID, [mail_group_id], partner_ids)
        return 1

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