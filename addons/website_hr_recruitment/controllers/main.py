# -*- coding: utf-8 -*-
from openerp.addons.web import http
from openerp.addons.web.http import request
import base64

from urllib import quote_plus

class website_hr_recruitment(http.Controller):

    @http.route(['/jobs'], type='http', auth="public")
    def jobs(self, mail_group_id=None, job_id=None, **post):
        website = request.registry['website']
        hr_job_obj = request.registry['hr.job']
        group_obj = request.registry['mail.group']
        user_obj = request.registry['res.users']
        
        jobpost_ids = hr_job_obj.search(request.cr, request.uid, [("state", 'in', ['recruit', 'open'])])
        request.cr.execute("select distinct(com.id) from hr_job job, res_company com where com.id=job.company_id")
        ids = []
        for i in request.cr.fetchall():
            ids.append(i[0])
        companies = request.registry['res.company'].browse(request.cr, request.uid, ids)
        values = website.get_rendering_context({
            'companies': companies,
            'res_job': hr_job_obj.browse(request.cr, request.uid, jobpost_ids),
            'subscribe': post.get('subscribe'),
            'job_id': None,
            'no_of_jobs': len(hr_job_obj.browse(request.cr, request.uid, jobpost_ids)),
        })
        if request.uid != website.get_public_user().id and mail_group_id:
            message_follower_ids = group_obj.read(request.cr, request.uid, [mail_group_id], ['message_follower_ids'])[0]['message_follower_ids']
            parent_id = user_obj.browse(request.cr, SUPERUSER_ID, request.uid).partner_id.id
            values['subscribe'] = parent_id in message_follower_ids
        
        if job_id:
            values['job_id'] = hr_job_obj.browse(request.cr, request.uid, job_id)

        return website.render("website_hr_recruitment.index", values)

    @http.route(['/jobs/subscribe'], type='http', auth="public")
    def subscribe(self, mail_group_id=None, job_id=None, **post):
        website = request.registry['website']
        partner_obj = request.registry['res.partner']
        group_obj = request.registry['mail.group']
        user_obj = request.registry['res.users']

        if mail_group_id and 'subscribe' in post and (post.get('email') or request.uid != website.get_public_user().id):
            if request.uid == website.get_public_user().id:
                partner_ids = partner_obj.search(request.cr, SUPERUSER_ID, [("email", "=", post.get('email'))])
                if not partner_ids:
                    partner_ids = [partner_obj.create(request.cr, SUPERUSER_ID, {"email": post.get('email'), "name": "Subscribe: %s" % post.get('email')})]
            else:
                partner_ids = [user_obj.browse(request.cr, request.uid, request.uid).partner_id.id]
            group_obj.check_access_rule(request.cr, request.uid, [mail_group_id], 'read')
            group_obj.message_subscribe(request.cr, SUPERUSER_ID, [mail_group_id], partner_ids)

        return self.jobs(mail_group_id=mail_group_id, job_id=job_id, subscribe=post.get('email'))

    @http.route(['/jobs/unsubscribe'], type='http', auth="public")
    def unsubscribe(self, mail_group_id=None, job_id=None, **post):
        website = request.registry['website']
        partner_obj = request.registry['res.partner']
        group_obj = request.registry['mail.group']
        user_obj = request.registry['res.users']

        if mail_group_id and 'unsubscribe' in post and (post.get('email') or request.uid != website.get_public_user().id):
            if request.uid == website.get_public_user().id:
                partner_ids = partner_obj.search(request.cr, SUPERUSER_ID, [("email", "=", post.get('email'))])
            else:
                partner_ids = [user_obj.browse(request.cr, request.uid, request.uid).partner_id.id]
            group_obj.check_access_rule(request.cr, request.uid, [mail_group_id], 'read')
            group_obj.message_unsubscribe(request.cr, SUPERUSER_ID, [mail_group_id], partner_ids)

        return self.jobs(mail_group_id=mail_group_id, job_id=job_id, subscribe=None)

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
# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
