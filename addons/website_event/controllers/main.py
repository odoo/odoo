# -*- coding: utf-8 -*-

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website import website
from openerp.tools.translate import _

from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import tools

class website_hr(http.Controller):

    @http.route(['/event', '/event/search/<path:path>'], type='http', auth="public")
    def blog(self, path=None, **post):
        data_obj = request.registry['event.event']

        def sd(date):
            return date.strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        today = datetime.today()
        dates = [
            [None, _('All Dates'), [(1, "=", 1)]],
            ['today', _('Today'), [
                ("date_begin", ">=", sd(today)),
                ("date_begin", "<", sd(today + relativedelta(days=1)))],
                0],
            ['tomorrow', _('Tomorrow'), [
                ("date_begin", ">=", sd(today + relativedelta(days=1))),
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

        obj_ids = data_obj.search(request.cr, request.uid, [(1, "=", 1)])
        values = {
            'event_ids': data_obj.browse(request.cr, request.uid, obj_ids),
            'dates': dates,
            'date_active': None,
        }

        html = website.render("website_event.index", values)
        return html

    @http.route(['/event/publish'], type='http', auth="public")
    def publish(self, **post):
        obj_id = int(post['id'])
        data_obj = request.registry['event.event']

        obj = data_obj.browse(request.cr, request.uid, obj_id)
        data_obj.write(request.cr, request.uid, [obj_id], {'website_published': not obj.website_published})
        obj = data_obj.browse(request.cr, request.uid, obj_id)

        return obj.website_published and "1" or "0"
