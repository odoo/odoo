from werkzeug.datastructures import MIMEAccept
from werkzeug.exceptions import NotAcceptable
from werkzeug.http import parse_accept_header

from odoo.http import content_disposition, Controller, request, route


class CalendarController(Controller):
    @route('/calendar.ics', type='http', auth='calendar_ics', save_session=False)
    def calendar_ics(self, key):
        """
        :param key: res.users.apikeys key
        """
        accept = parse_accept_header(request.httprequest.headers.get('Accept'), MIMEAccept)
        if accept and not accept.best_match(['text/calendar']):
            raise NotAcceptable()

        domain = request.env['res.users'].browse(request.uid)._get_ics_domain()
        events = request.env['calendar.event'].with_user(request.uid).search(domain)
        data = events.ics()
        headers = [
            ('Content-Disposition', content_disposition('calendar.ics')),
            ('Content-Length', len(data)),
            ('Content-Type', 'text/calendar'),
        ]
        return request.make_response(data, headers)
