from odoo import http, _
from odoo.http import request


class UniversityCoursesController(http.Controller):

    @http.route(['/courses', '/courses/degree/<string:degree_type>'], type='http', auth='public', website=True, sitemap=True)
    def courses_list(self, degree_type=None, search=None, **kw):
        Program = request.env['university.program'].sudo()
        domain = [('active', '=', True)]

        if degree_type:
            domain.append(('degree_type', '=', degree_type))
        if search:
            domain.append(('name', 'ilike', search.strip()))

        programs = Program.search(domain, order='degree_type, name')
        degree_types = [
            ('bachelor', _('Bachelor')),
            ('master', _('Master')),
            ('doctorate', _('Doctorate')),
            ('diploma', _('Diploma')),
        ]

        values = {
            'programs': programs,
            'degree_types': degree_types,
            'current_degree': degree_type,
            'search_term': search or '',
            'total_programs': len(programs),
        }
        return request.render('school_website.courses_catalog_template', values)

    @http.route(['/courses/<int:program_id>'], type='http', auth='public', website=True, sitemap=True)
    def course_detail(self, program_id, **kw):
        program = request.env['university.program'].sudo().browse(program_id)
        if not program.exists():
            return request.not_found()

        # Find curriculum / subjects for this program if available
        curricula = request.env['university.curriculum'].sudo().search([
            ('program_id', '=', program.id),
        ], order='semester_id')

        values = {
            'program': program,
            'curricula': curricula,
        }
        return request.render('school_website.course_detail_template', values)
