# -*- coding: utf-8 -*-
import base64

from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.tools.translate import _
from openerp.addons.web.http import request

class website_hr_recruitment(http.Controller):
    @http.route([
        '/jobs',
        '/jobs/country/<model("res.country"):country>',
        '/jobs/department/<model("hr.department"):department>',
        '/jobs/country/<model("res.country"):country>/department/<model("hr.department"):department>',
        '/jobs/office/<int:office_id>',
        '/jobs/country/<model("res.country"):country>/office/<int:office_id>',
        '/jobs/department/<model("hr.department"):department>/office/<int:office_id>',
        '/jobs/country/<model("res.country"):country>/department/<model("hr.department"):department>/office/<int:office_id>',
        ], type='http', auth="public", website=True)
    def jobs(self, country=None, department=None, office_id=None):
        context=dict(request.context, show_address=True, no_tag_br=True)
        cr, uid = request.cr, request.uid

        # Search all available jobs as uid
        JobsObj = request.registry['hr.job']
        job_ids = JobsObj.search(cr, uid, [], order="website_published desc,no_of_recruitment desc", context=context)

        # Browse jobs as superuser, because address is restricted
        jobs = JobsObj.browse(cr, 1, job_ids, context=context)

        # Deduce departments and offices of those jobs
        countries = set(j.address_id.country_id for j in jobs if j.address_id and j.address_id.country_id)
        departments = set(j.department_id for j in jobs if j.department_id)
        offices = set(j.address_id for j in jobs if j.address_id)
        countries = set(o.country_id for o in offices if o.country_id)

        # Default search by user country
        if not country and not department and not office_id:
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                country_ids = request.registry.get('res.country').search(cr, uid, [('code', '=', country_code)], context=context)
                if country_ids:
                    country = country_ids[0]

        # Filter the matching one
        jobs = [j for j in jobs if country==None or j.address_id==None or j.address_id.country_id and j.address_id.country_id.id == country.id]
        jobs = [j for j in jobs if department==None or j.department_id and j.department_id.id == department.id]
        jobs = [j for j in jobs if office_id==None or j.address_id and j.address_id.id == office_id]

        # Render page
        return request.website.render("website_hr_recruitment.index", {
            'jobs': jobs,
            'countries': countries,
            'departments': departments,
            'offices': offices,
            'country_id': country,
            'department_id': department,
            'office_id': office_id,
            'countries': countries
        })

    @http.route('/jobs/add', type='http', auth="user", website=True)
    def jobs_add(self, **kwargs):
        cr, uid, context = request.cr, request.uid, request.context
        value = {
            'name': _('New Job Offer'),
        }
        job_id = request.registry.get('hr.job').create(cr, uid, value, context=context)
        return request.redirect("/jobs/detail/%s?enable_editor=1" % job_id)

    @http.route(['/jobs/detail/<model("hr.job"):job>'], type='http', auth="public", website=True)
    def jobs_detail(self, job, **kwargs):
        return request.website.render("website_hr_recruitment.detail", { 'job': job, 'main_object': job })

    @http.route(['/jobs/apply/<model("hr.job"):job>'], type='http', auth="public", website=True)
    def jobs_apply(self, job):
        error = {}
        default = {}
        if 'website_hr_recruitment_error' in request.session:
            error = request.session.pop('website_hr_recruitment_error')
            default = request.session.pop('website_hr_recruitment_default')
        return request.website.render("website_hr_recruitment.apply", { 'job': job, 'error': error, 'default': default})

    @http.route(['/jobs/thankyou'], methods=['POST'], type='http', auth="public", website=True)
    def jobs_thankyou(self, **post):
        cr, uid, context = request.cr, request.uid, request.context
        imd = request.registry['ir.model.data']

        error = {}
        for field_name in ["partner_name", "phone", "email_from"]:
            if not post.get(field_name):
                error[field_name] = 'missing'
        if error:
            request.session['website_hr_recruitment_error'] = error
            ufile = post.pop('ufile')
            if ufile:
                error['ufile'] = 'reset'
            request.session['website_hr_recruitment_default'] = post
            return request.redirect('/jobs/apply/%s' % post.get("job_id"))

        value = {
            'source_id' : imd.xmlid_to_res_id(cr, SUPERUSER_ID, 'hr_recruitment.source_website_company'),
            'name': '%s\'s Application' % post.get('partner_name'), 
        }
        for f in ['email_from', 'partner_name', 'description']:
            value[f] = post.get(f)
        for f in ['department_id', 'job_id']:
            value[f] = int(post.get(f) or 0)
        # Retro-compatibility for saas-3. "phone" field should be replace by "partner_phone" in the template in trunk.
        value['partner_phone'] = post.pop('phone', False)

        applicant_id = request.registry['hr.applicant'].create(cr, SUPERUSER_ID, value, context=context)
        if post['ufile']:
            attachment_value = {
                'name': post['ufile'].filename,
                'res_name': value['partner_name'],
                'res_model': 'hr.applicant',
                'res_id': applicant_id,
                'datas': base64.encodestring(post['ufile'].read()),
                'datas_fname': post['ufile'].filename,
            }
            request.registry['ir.attachment'].create(cr, SUPERUSER_ID, attachment_value, context=context)
        return request.website.render("website_hr_recruitment.thankyou", {})

# vim :et:
