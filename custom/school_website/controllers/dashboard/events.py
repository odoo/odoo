from odoo import http, _
from odoo.http import request


class UniversityEventsController(http.Controller):

    @http.route(['/events', '/events/category/<string:notice_type>'], type='http', auth='public', website=True, sitemap=True)
    def events_list(self, notice_type=None, search=None, **kw):
        Notice = request.env['university.notice.board'].sudo()
        domain = [('target_audience', 'in', ['all', 'students', 'graduating'])]

        if notice_type:
            domain.append(('notice_type', '=', notice_type))
        if search:
            domain.append(('name', 'ilike', search.strip()))

        notices = Notice.search(domain, order='pinned desc, date desc')
        categories = [
            ('event', _('Campus Events & Summits')),
            ('academic', _('Academic Announcements')),
            ('exam', _('Exams & Timetables')),
            ('holiday', _('Holidays & Breaks')),
        ]

        values = {
            'notices': notices,
            'categories': categories,
            'current_category': notice_type,
            'search_term': search or '',
        }
        return request.render('school_website.events_list_template', values)
