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

    url = fields.Char(string='Full URL', required=True)
    code = fields.Char(string='Short URL Code', store=True, compute='_get_random_code_string')
    count = fields.Integer(string='Number of Clicks', compute='_count_url')

    @api.one
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

    @api.model
    def create_shorten_url(self, url):
        if not VALIDATE_URL(url): return False
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        return urljoin(base_url, '/r/%(code)s' % {'code': self.create({'url':url}).code,})

    @api.model
    def get_url_from_code(self, code, ip, country_code, stat_id=False):
        record = self.sudo().search_read([('code', '=', code)], ['url'])
        website_alias_click = self.env['website.alias.click']
        again = website_alias_click.sudo().search_read([('alias_id', '=', record[0]['id']), ('ip', '=', ip)], ['id'])
        rec = record and record[0] or False
        if rec:
            if not again:
                country_id = self.env['res.country'].sudo().search([('code', '=', country_code)])
                vals = {
                        'alias_id':rec.get('id'),
                        'create_date':datetime.datetime.now().date(),
                        'ip':ip,
                        'country_id': country_id and country_id[0] or False,
                        'mail_stat_id': stat_id
                }
                website_alias_click.sudo().create(vals)
            return rec.get('url')

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
