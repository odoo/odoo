import string
import random
import datetime
from urlparse import urlparse
from urlparse import urljoin
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
    count = fields.Integer(string='Number of Clicks', compute='_count_url')
    short_url = fields.Char(string="Short URL", compute='_short_url')
    alias_click_ids = fields.One2many('website.alias.click', 'alias_id', string='Clicks')
    is_archived = fields.Boolean(string='Archived', default=False)

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

        return {'code':self.code, 'count':self.count, 'url':self.url, 'write_date':self.write_date, 'short_url':self.short_url,
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
    def recent_links(self):
        return self.search([('is_archived', '=', False)], order='write_date ASC')

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

        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        alias = self.create(dict({'url':url}.items() + tracking_fields.items()))

        return alias

    # TO SPLIT : unclear
    @api.model
    def get_url_from_code(self, code, ip, country_code, stat_id=False, context=None):

        print 'get_url_from_code'

        rec = self.sudo().search([('code', '=', code)])

        if rec:
            again = rec.alias_click_ids.sudo().search_count([('alias_id', '=', rec.id), ('ip', '=', ip)])

            # if not again:
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
            SELECT to_char(create_date, 'YYYY-MM-DD'), count(id)
            FROM website_alias_click
            WHERE alias_id = '%s'
            GROUP BY to_char(create_date, 'YYYY-MM-DD')
        """, (alias_id, ))

        return self.env.cr.dictfetchall()

    @api.model
    def get_total_clicks(self, alias_id):
        return self.search_count([('alias_id', '=', alias_id)])

    @api.model
    def get_clicks_by_country(self, alias_id):
        self.env.cr.execute("""
            SELECT rc.name, count(wac.id)
            FROM website_alias_click wac
            LEFT OUTER JOIN res_country rc
            ON wac.country_id = rc.id
            WHERE wac.alias_id = '%s'
            GROUP BY wac.country_id, rc.name
        """, (alias_id, ))

        return self.env.cr.dictfetchall()
