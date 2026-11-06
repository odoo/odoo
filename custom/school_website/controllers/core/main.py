from odoo import http, _
from odoo.http import request


class UniversityMainController(http.Controller):

    @http.route(['/jobs'], type='http', auth='public', website=True, sitemap=True)
    def university_jobs(self, **kw):
        departments = request.env['university.department'].sudo().search([('active', '=', True)])
        values = {
            'departments': departments,
        }
        return request.render('school_website.jobs_page_template', values)

    @http.route(['/aboutus', '/about'], type='http', auth='public', website=True, sitemap=True)
    def university_about(self, **kw):
        departments = request.env['university.department'].sudo().search([('active', '=', True)], limit=6)
        values = {
            'departments': departments,
        }
        return request.render('school_website.about_page_template', values)

    @http.route(['/contact'], type='http', auth='public', website=True, sitemap=True)
    def university_contact_redirect(self, **kw):
        return request.redirect('/contactus')
