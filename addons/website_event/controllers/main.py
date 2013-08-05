# -*- coding: utf-8 -*-

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website import website
from openerp.tools.translate import _

from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import tools

class website_hr(http.Controller):

    @http.route(['/event', '/event/search/<path:searches>'], type='http', auth="public")
    def events(self, searches=None, **post):
        data_obj = request.registry['event.event']

        _search = {}
        for search in searches.split("/"):
            search = search.split("-")
            if len(search) == 2:
                _search[search[0]] = [search[1], []]

        def sd(date):
            return date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        today = datetime.today()
        dates = [
            ['all', _('All Dates'), [(1, "=", 1)], 0],
            ['today', _('Today'), [
                ("date_begin", ">", sd(today)),
                ("date_begin", "<", sd(today + relativedelta(days=1)))],
                0],
            ['tomorrow', _('Tomorrow'), [
                ("date_begin", ">", sd(today + relativedelta(days=1))),
                ("date_begin", "<", sd(today + relativedelta(days=2)))],
                0],
            ['week', _('This Week'), [
                ("date_begin", ">=", sd(today + relativedelta(days=-today.weekday()))),
                ("date_begin", "<", sd(today  + relativedelta(days=6-today.weekday())))],
                0],
            ['nextweek', _('Next Week'), [
                ("date_begin", ">=", sd(today + relativedelta(days=7-today.weekday()))),
                ("date_begin", "<", sd(today  + relativedelta(days=13-today.weekday())))],
                0],
            ['month', _('This month'), [
                ("date_begin", ">=", sd(today.replace(day=1) + relativedelta(months=1))),
                ("date_begin", "<", sd(today.replace(day=1)  + relativedelta(months=1)))],
                0],
        ]

        # search domains
        for date in dates:
            if _search.get("date") and _search["date"][0] == date[0]:
                _search["date"].append(date[2])

        # count by domains without self search
        for date in dates:
            domain = [(1, "=", 1)]
            for key, search in _search.items():
                if key != 'date':
                    domain += search[1]
            date[3] = data_obj.search(request.cr, request.uid, domain + date[2], count=True)

        # domain and search_path
        domain = [(1, "=", 1)]
        search_path = '/search'
        for key, search in _search.items():
            search_path = "%s/%s-%s" % (search_path, key, search[0])
            domain += search[1]

        obj_ids = data_obj.search(request.cr, request.uid, domain)
        values = {
            'event_ids': data_obj.browse(request.cr, request.uid, obj_ids),
            'dates': dates,
            'search': _search,
            'search_path': search_path,
        }

        html = website.render("website_event.index", values)
        return html

    @http.route(['/event/<int:event_id>'], type='http', auth="public")
    def event(self, event_id=None, **post):
        return ""

    @http.route(['/event/publish'], type='http', auth="public")
    def publish(self, **post):
        obj_id = int(post['id'])
        data_obj = request.registry['event.event']

        obj = data_obj.browse(request.cr, request.uid, obj_id)
        data_obj.write(request.cr, request.uid, [obj_id], {'website_published': not obj.website_published})
        obj = data_obj.browse(request.cr, request.uid, obj_id)

        return obj.website_published and "1" or "0"
