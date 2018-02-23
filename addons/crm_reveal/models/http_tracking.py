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
        if view and self.env['crm.reveal.rule'].sudo().match_url(res.get('url', '')):
            res.update({
                'reveal': True,
                'trakable': True
            })
        return res

    # def get_vals(self, request):
    #     res = super(HTTPPageView, self).get_vals(request)
    #     res.update({
    #         'reveal': True
    #     })
    #     return res
