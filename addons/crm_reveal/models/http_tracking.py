import re
from odoo import fields, models, SUPERUSER_ID, tools, api
from psycopg2 import IntegrityError
from odoo.tools import html_escape

class HTTPTracking(models.Model):
    _inherit = 'http.session'

    lead_id = fields.Many2one('crm.lead', string='Lead')


class HTTPPageView(models.Model):
    _inherit = 'http.pageview'

    crm_reveal_scanned = fields.Boolean(string='CRM Reveal IP Scanned')
    reveal = fields.Boolean(string='is generated from reveal')

    def is_trackable(self, view, request):
        res = super(HTTPPageView, self).is_trackable(view, request)
        url = res.get('url', '')
        if self.env['crm.reveal.rule'].sudo().match_url(url):
            with self.pool.cursor() as pv_cr:
                pv_cr.execute('''
                    UPDATE http_pageview SET view_date=%s , reveal=True  WHERE session_id=%s AND url=%s RETURNING id;
                    ''', (res.get('view_date'), res.get('session_id', 0), url))
                fetch = pv_cr.fetchone()
                if fetch:
                    return res
                else:
                    res.update({
                        'reveal': True,
                        'trakable': True
                    })
        return res
