import re
from odoo import fields, models, SUPERUSER_ID, tools, api
from psycopg2 import IntegrityError
from odoo.tools import html_escape

class HTTPTracking(models.Model):
    _inherit = 'http.session'

    lead_id = fields.Many2one('crm.lead', string='Lead')


class HTTPURLRegex(models.Model):
    _name = 'http.url.track'

    regex_url = fields.Char(string='URL Regex')

    @api.model
    @tools.ormcache()
    def get_regex(self):
        return self.search([]).mapped('regex_url')

    def match_url(self, url):
        if re.findall('|'.join([rg for rg in self.get_regex() if rg]), url):
            return True
        return False


class HTTPPageView(models.Model):
    _inherit = 'http.pageview'

    crm_reveal_scanned = fields.Boolean(string='CRM Reveal IP Scanned')

    def is_trackable(self, view, url):
        res = super(HTTPPageView, self).is_trackable(view, url)
        if not res and view and self.env['http.url.track'].sudo().match_url(url):
            return True
        return res
