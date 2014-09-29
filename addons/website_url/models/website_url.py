import string
import random
import datetime
from urlparse import urlparse
from urlparse import urljoin
from openerp.osv import osv, fields
from openerp import models, fields, api, _

ALLOWED_SCHEMES = ['http', 'https', 'ftp', 'ftps']

def VALIDATE_URL(url):
    return urlparse(url)[0] in ALLOWED_SCHEMES and 2048 >= len(url)

class website_alias(models.Model):
    _name = "website.alias"
    _rec_name = "code"

    _inherit = ['crm.tracking.mixin']

    url = fields.Char(string='Full URL', required=True)
    code = fields.Char(string='Short URL Code', store=True, compute='_get_random_code_string')
    count = fields.Integer(string='Number of Clicks', compute='_count_url', store=True)
    short_url = fields.Char(string="Short URL", compute='_short_url')
    alias_clicks = fields.One2many('website.alias.click', 'alias_id', string='Clicks')
    is_archived = fields.Boolean(string='Archived', default=False)

    @api.one
    @api.depends('alias_clicks.id')
    def _count_url(self):
        click_obj = self.env['website.alias.click']
        self.count = click_obj.search_count([('alias_id', '=', self.id)])

    @api.one
    def alias_click(self):
        for click in self.browse():
            return self.env['website.alias'].search([('id', '=', click.alias_id.id)])
        return []
 
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
        # because we integreted the names of the UTMs (like source_id.name)

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

        print tracking_fields

        if not VALIDATE_URL(url): return False

        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        alias = self.create(dict({'url':url}.items() + tracking_fields.items()))

        return alias

    @api.model
    def get_url_from_code(self, code, ip, country_code, stat_id=False, context=None):

        record = self.sudo().search([('code', '=', code)])
        rec = record and record[0] or False

        if rec:
            website_alias_click = self.env['website.alias.click']
            again = website_alias_click.sudo().search_read([('alias_id', '=', rec.id), ('ip', '=', ip)], ['id'])

            if not again:
                country_id = self.env['res.country'].sudo().search([('code', '=', country_code)])
                vals = {
                    'alias_id':rec.id,
                    'create_date':datetime.datetime.now().date(),
                    'ip':ip,
                    'country_id': country_id and country_id[0] or False,
                    'mail_stat_id': stat_id
                }
                website_alias_click.sudo().create(vals) 

            crm_tracking_mixin = self.env['crm.tracking.mixin']
            
            parsed = urlparse(rec.url)
            utms = ''

            for key, field in crm_tracking_mixin.tracking_fields():
                if getattr(rec, field).name:
                    utms += key + '=' + getattr(rec, field).name + '&'

            return '%s://%s%s?%s%s#%s' % (parsed.scheme, parsed.netloc, parsed.path, utms, parsed.query, parsed.fragment)
        else:
            return None

    sql_constraints = [
        ('code', 'unique( code )', 'Code must be unique.'),
    ]

class website_alias_click(models.Model):
    _name = "website.alias.click"
    _rec_name = "alias_id"

    click_date = fields.Date(string='Create Date')
    alias_id = fields.Many2one('website.alias','Alias')
    ip = fields.Char(string='Internet Protocol')
    country_id = fields.Many2one('res.country','Country')
