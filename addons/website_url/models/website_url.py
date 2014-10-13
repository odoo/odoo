import string
import random
import datetime
from urllib2 import urlopen
from lxml.html import parse
from urlparse import urljoin
from urlparse import urlparse
from openerp import models, fields, api, _

ALLOWED_SCHEMES = ['http', 'https', 'ftp', 'ftps']

def VALIDATE_URL(url):

    if not url.startswith('http'):
        return 'http://' + url

    return url

class website_alias(models.Model):
    _name = "website.alias"
    _rec_name = "code"

    _inherit = ['crm.tracking.mixin']

    url = fields.Char(string='Full URL', required=True)
    code = fields.Char(string='Short URL Code', store=True, compute='_get_random_code_string')
    count = fields.Integer(string='Number of Clicks', compute='_count_url', store=True)
    short_url = fields.Char(string="Short URL", compute='_short_url')
    alias_click_ids = fields.One2many('website.alias.click', 'alias_id', string='Clicks')
    is_archived = fields.Boolean(string='Archived', default=False)
    title = fields.Char(string="Title of the alias", store=True)
    favicon = fields.Char(string="Favicon", store=True)

    @api.one
    @api.depends('alias_click_ids')
    def _count_url(self):
        self.count =  len(self.alias_click_ids)
 
    @api.one
    @api.depends('url')
    def _get_random_code_string(self):
        def random_string(id):
            size = 3
            while True:
                x = ''.join(random.choice(string.letters + string.digits) for _ in range(size))
                if not x: 
                    size += 1 
                else:
                    return x + str(id)
        self.code = random_string(self.id)

    @api.one
    @api.depends('code')
    def _short_url(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        self.short_url = urljoin(base_url, '/r/%(code)s' % {'code': self.code,})

    @api.one
    def to_json(self):

        # We use a custom method to convert the record to a dictionnary (instead of .read)
        # because we insert the names of the UTMs (like source_id.name)
        return {'title':self.title, 'code':self.code, 'count':self.count, 'url':self.url, 'host':urlparse(self.url).netloc, 'write_date':self.write_date, 
                'short_url':self.short_url, 'stats_url':self.short_url + '+', 'icon_src':'data:image/png;base64,' + self.favicon,
                    'campaign_id':{'name': (self.campaign_id.name if self.campaign_id.name else '')},
                    'medium_id':{'name':self.medium_id.name if self.medium_id.name else ''},
                    'source_id':{'name':self.source_id.name if self.source_id.name else ''}}

    @api.one
    def archive(self):
        return self.update({'is_archived':True})

    @api.multi
    def action_view_statistics(self):
        action = self.env['ir.actions.act_window'].for_xml_id('website_url', 'action_view_click_statistics')
        action['domain'] = [('alias_id', '=', self.id)]
        return action

    @api.multi
    def action_visit_page(self):
        return {
            'name' : _("Visit Webpage"),
            'type' : 'ir.actions.act_url',
            'url' : self.url,
            'target' : 'self',
        }

    @api.model
    def recent_links(self, filter):
        if filter == 'newest':
            return self.search([('is_archived', '=', False)], order='create_date DESC', limit=20)
        elif filter == 'most-clicked':
            return self.search([('is_archived', '=', False)], order='count DESC', limit=20)
        elif filter == 'recently-used':
            return self.search([('is_archived', '=', False), ('count', '!=', 0)], order='write_date DESC', limit=20)
        else:
            return {'Error':"THis filter doesn't exist."}

    @api.model
    def create_shorten_url(self, url, tracking_fields):
        url = VALIDATE_URL(url)

        # Check if there is already an alias with the same URL and UTMs
        search_domain = [('url', '=', url)]

        for key, field in self.env['crm.tracking.mixin'].tracking_fields():
            if field in tracking_fields:
                search_domain.append((field, '=', int(tracking_fields[field])))
            else:
                search_domain.append((field, '=', None))

        result = self.search(search_domain, limit=1)

        if result:
            # Put the old link on top of recently generated links
            # (recent links are sorted by 'write_date')
            result.update({'is_archived':False})
            return result
        else:
            # Try to get the title of the page
            try:
                page = urlopen(url)
                p = parse(page)
                title = p.find('.//title').text
            except:
                raise BaseException("URL not found")
                title = 'Page not found (404)'
                
            # Try to get the favicon of the page
            try:
                icon = urlopen('http://www.google.com/s2/favicons?domain=' + url).read()
                icon_base64 = icon.encode('base64').replace("\n", "")
            except:
                icon_base64 = 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsSAAALEgHS3X78AAACiElEQVQ4EaVTzU8TURCf2tJuS7tQtlRb6UKBIkQwkRRSEzkQgyEc6lkOKgcOph78Y+CgjXjDs2i44FXY9AMTlQRUELZapVlouy3d7kKtb0Zr0MSLTvL2zb75eL838xtTvV6H/xELBptMJojeXLCXyobnyog4YhzXYvmCFi6qVSfaeRdXdrfaU1areV5KykmX06rcvzumjY/1ggkR3Jh+bNf1mr8v1D5bLuvR3qDgFbvbBJYIrE1mCIoCrKxsHuzK+Rzvsi29+6DEbTZz9unijEYI8ObBgXOzlcrx9OAlXyDYKUCzwwrDQx1wVDGg089Dt+gR3mxmhcUnaWeoxwMbm/vzDFzmDEKMMNhquRqduT1KwXiGt0vre6iSeAUHNDE0d26NBtAXY9BACQyjFusKuL2Ry+IPb/Y9ZglwuVscdHaknUChqLF/O4jn3V5dP4mhgRJgwSYm+gV0Oi3XrvYB30yvhGa7BS70eGFHPoTJyQHhMK+F0ZesRVVznvXw5Ixv7/C10moEo6OZXbWvlFAF9FVZDOqEABUMRIkMd8GnLwVWg9/RkJF9sA4oDfYQAuzzjqzwvnaRUFxn/X2ZlmGLXAE7AL52B4xHgqAUqrC1nSNuoJkQtLkdqReszz/9aRvq90NOKdOS1nch8TpL555WDp49f3uAMXhACRjD5j4ykuCtf5PP7Fm1b0DIsl/VHGezzP1KwOiZQobFF9YyjSRYQETRENSlVzI8iK9mWlzckpSSCQHVALmN9Az1euDho9Xo8vKGd2rqooA8yBcrwHgCqYR0kMkWci08t/R+W4ljDCanWTg9TJGwGNaNk3vYZ7VUdeKsYJGFNkfSzjXNrSX20s4/h6kB81/271ghG17l+rPTAAAAAElFTkSuQmCC'

        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        alias = self.create(dict({'url':url, 'title':title, 'favicon':icon_base64}.items() + tracking_fields.items()))

        return alias

    # TO SPLIT : unclear
    @api.model
    def get_url_from_code(self, code, ip, country_code, stat_id=False, context=None):

        rec = self.sudo().search([('code', '=', code)])

        if rec:
            again = rec.alias_click_ids.sudo().search_count([('alias_id', '=', rec.id), ('ip', '=', ip)])

            if not again:
                country_record = self.env['res.country'].sudo().search([('code', '=', country_code)], limit=1).read(['id'])

                vals = {
                    'alias_id':rec.id,
                    'create_date':datetime.date.today(),
                    'ip':ip,
                    'country_id': country_record[0]['id'] if country_record else False,
                    'mail_stat_id': stat_id
                }
                self.env['website.alias.click'].sudo().create(vals)
            
            parsed = urlparse(rec.url)
            utms = ''

            for key, field in self.env['crm.tracking.mixin'].tracking_fields():
                attr = getattr(rec, field).name
                if attr:
                    utms += key + '=' + attr + '&'

            return '%s://%s%s?%s%s#%s' % (parsed.scheme, parsed.netloc, parsed.path, utms, parsed.query, parsed.fragment)
        else:
            return None

    sql_constraints = [
        ('code', 'unique( code )', 'Code must be unique.'),
    ]

class website_alias_click(models.Model):
    _name = "website.alias.click"
    _rec_name = "alias_id"

    click_date = fields.Date(string='Create Date') # Override create_date
    alias_id = fields.Many2one('website.alias','Alias', required=True)
    ip = fields.Char(string='Internet Protocol')
    country_id = fields.Many2one('res.country','Country')

    @api.model
    def get_clicks_by_day(self, alias_id):
        self.env.cr.execute("""
            SELECT to_char(create_date, 'YYYY-MM-DD'), COUNT(id)
            FROM website_alias_click
            WHERE alias_id = '%s'
            GROUP BY to_char(create_date, 'YYYY-MM-DD')
            ORDER BY to_char(create_date, 'YYYY-MM-DD') DESC
        """, (alias_id, ))

        return self.env.cr.dictfetchall()

    @api.model
    def get_total_clicks(self, alias_id):
        return self.search_count([('alias_id', '=', alias_id)])

    @api.model
    def get_clicks_by_country(self, alias_id):
        self.env.cr.execute("""
            SELECT rc.name, COUNT(wac.id)
            FROM website_alias_click wac
            LEFT OUTER JOIN res_country rc
            ON wac.country_id = rc.id
            WHERE wac.alias_id = '%s'
            GROUP BY wac.country_id, rc.name
        """, (alias_id, ))

        return self.env.cr.dictfetchall()

    @api.model
    def get_last_month_clicks_by_country(self, alias_id):
        self.env.cr.execute("""
            SELECT rc.name, COUNT(wac.id)
            FROM website_alias_click wac
            LEFT OUTER JOIN res_country rc
            ON wac.country_id = rc.id
            WHERE wac.alias_id = '%s' AND wac.create_date > now() - interval '1 month'
            GROUP BY wac.country_id, rc.name
        """, (alias_id, ))

        return self.env.cr.dictfetchall()

    @api.model
    def get_last_week_clicks_by_country(self, alias_id):
        self.env.cr.execute("""
            SELECT rc.name, COUNT(wac.id)
            FROM website_alias_click wac
            LEFT OUTER JOIN res_country rc
            ON wac.country_id = rc.id
            WHERE wac.alias_id = '%s' AND wac.create_date > now() - interval '7 days'
            GROUP BY wac.country_id, rc.name
        """, (alias_id, ))

        return self.env.cr.dictfetchall()
