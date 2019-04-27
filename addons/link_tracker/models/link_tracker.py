# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import random
import re
import requests
import string

from lxml import html
from werkzeug import urls, utils

from odoo import models, fields, api, _


URL_REGEX = r'(\bhref=[\'"](?!mailto:|tel:|sms:)([^\'"]+)[\'"])'


def VALIDATE_URL(url):
    if urls.url_parse(url).scheme not in ('http', 'https', 'ftp', 'ftps'):
        return 'http://' + url

    return url


class LinkTracker(models.Model):
    """ Link trackers allow users to wrap any URL into a short URL that can be
    tracked by Odoo. Clicks are counter on each link. A tracker is linked to
    UTMs allowing to analyze marketing actions.

    This model is also used in mass_mailing where each link in html body is
    automatically converted into a short link that is tracked and integrates
    UTMs. """
    _name = "link.tracker"
    _rec_name = "short_url"
    _description = "Link Tracker"
    _inherit = ["utm.mixin"]

    # URL info
    url = fields.Char(string='Target URL', required=True)
    short_url = fields.Char(string='Tracked URL', compute='_compute_short_url')
    redirected_url = fields.Char(string='Redirected URL', compute='_compute_redirected_url')
    short_url_host = fields.Char(string='Host of the short URL', compute='_compute_short_url_host')
    title = fields.Char(string='Page Title', store=True)
    favicon = fields.Char(string='Favicon', compute='_compute_favicon', store=True)
    icon_src = fields.Char(string='Favicon Source', compute='_compute_icon_src')
    # Tracking
    link_code_ids = fields.One2many('link.tracker.code', 'link_id', string='Codes')
    code = fields.Char(string='Short URL code', compute='_compute_code')
    link_click_ids = fields.One2many('link.tracker.click', 'link_id', string='Clicks')
    count = fields.Integer(string='Number of Clicks', compute='_compute_count', store=True)

    @api.one
    @api.depends('link_click_ids.link_id')
    def _compute_count(self):
        self.count = len(self.link_click_ids)

    @api.one
    @api.depends('code')
    def _compute_short_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        self.short_url = urls.url_join(base_url, '/r/%(code)s' % {'code': self.code})

    @api.one
    def _compute_short_url_host(self):
        self.short_url_host = self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/r/'

    @api.one
    def _compute_code(self):
        record = self.env['link.tracker.code'].search([('link_id', '=', self.id)], limit=1, order='id DESC')
        self.code = record.code

    @api.one
    @api.depends('favicon')
    def _compute_icon_src(self):
        self.icon_src = 'data:image/png;base64,' + self.favicon

    @api.one
    @api.depends('url')
    def _compute_redirected_url(self):
        parsed = urls.url_parse(self.url)

        utms = {}
        for key, field, cook in self.env['utm.mixin'].tracking_fields():
            attr = getattr(self, field).name
            if attr:
                utms[key] = attr
        utms.update(parsed.decode_query())

        self.redirected_url = parsed.replace(query=urls.url_encode(utms)).to_url()

    @api.model
    @api.depends('url')
    def _get_title_from_url(self, url):
        try:
            page = requests.get(url, timeout=5)
            p = html.fromstring(page.text.encode('utf-8'), parser=html.HTMLParser(encoding='utf-8'))
            title = p.find('.//title').text
        except:
            title = url

        return title

    @api.one
    @api.depends('url')
    def _compute_favicon(self):
        try:
            icon = requests.get('http://www.google.com/s2/favicons', params={'domain': self.url}, timeout=5).content
            icon_base64 = base64.b64encode(icon).replace(b"\n", b"").decode('ascii')
        except:
            icon_base64 = 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsSAAALEgHS3X78AAACiElEQVQ4EaVTzU8TURCf2tJuS7tQtlRb6UKBIkQwkRRSEzkQgyEc6lkOKgcOph78Y+CgjXjDs2i44FXY9AMTlQRUELZapVlouy3d7kKtb0Zr0MSLTvL2zb75eL838xtTvV6H/xELBptMJojeXLCXyobnyog4YhzXYvmCFi6qVSfaeRdXdrfaU1areV5KykmX06rcvzumjY/1ggkR3Jh+bNf1mr8v1D5bLuvR3qDgFbvbBJYIrE1mCIoCrKxsHuzK+Rzvsi29+6DEbTZz9unijEYI8ObBgXOzlcrx9OAlXyDYKUCzwwrDQx1wVDGg089Dt+gR3mxmhcUnaWeoxwMbm/vzDFzmDEKMMNhquRqduT1KwXiGt0vre6iSeAUHNDE0d26NBtAXY9BACQyjFusKuL2Ry+IPb/Y9ZglwuVscdHaknUChqLF/O4jn3V5dP4mhgRJgwSYm+gV0Oi3XrvYB30yvhGa7BS70eGFHPoTJyQHhMK+F0ZesRVVznvXw5Ixv7/C10moEo6OZXbWvlFAF9FVZDOqEABUMRIkMd8GnLwVWg9/RkJF9sA4oDfYQAuzzjqzwvnaRUFxn/X2ZlmGLXAE7AL52B4xHgqAUqrC1nSNuoJkQtLkdqReszz/9aRvq90NOKdOS1nch8TpL555WDp49f3uAMXhACRjD5j4ykuCtf5PP7Fm1b0DIsl/VHGezzP1KwOiZQobFF9YyjSRYQETRENSlVzI8iK9mWlzckpSSCQHVALmN9Az1euDho9Xo8vKGd2rqooA8yBcrwHgCqYR0kMkWci08t/R+W4ljDCanWTg9TJGwGNaNk3vYZ7VUdeKsYJGFNkfSzjXNrSX20s4/h6kB81/271ghG17l+rPTAAAAAElFTkSuQmCC'

        self.favicon = icon_base64

    @api.model
    def create(self, vals):
        create_vals = vals.copy()

        if 'url' not in create_vals:
            raise ValueError('URL field required')
        else:
            create_vals['url'] = VALIDATE_URL(vals['url'])

        search_domain = []
        for fname, value in create_vals.items():
            search_domain.append((fname, '=', value))

        result = self.search(search_domain, limit=1)

        if result:
            return result

        if not create_vals.get('title'):
            create_vals['title'] = self._get_title_from_url(create_vals['url'])

        # Prevent the UTMs to be set by the values of UTM cookies
        for (key, fname, cook) in self.env['utm.mixin'].tracking_fields():
            if fname not in create_vals:
                create_vals[fname] = False

        link = super(LinkTracker, self).create(create_vals)

        code = self.env['link.tracker.code'].get_random_code_string()
        self.env['link.tracker.code'].sudo().create({'code': code, 'link_id': link.id})

        return link

    @api.model
    def convert_links(self, html, vals, blacklist=None):
        for match in re.findall(URL_REGEX, html):

            short_schema = self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/r/'

            href = match[0]
            long_url = match[1]

            vals['url'] = utils.unescape(long_url)

            if not blacklist or not [s for s in blacklist if s in long_url] and not long_url.startswith(short_schema):
                link = self.create(vals)
                shorten_url = self.browse(link.id)[0].short_url

                if shorten_url:
                    new_href = href.replace(long_url, shorten_url)
                    html = html.replace(href, new_href)

        return html

    @api.multi
    def action_view_statistics(self):
        action = self.env['ir.actions.act_window'].for_xml_id('link_tracker', 'link_tracker_click_action_statistics')
        action['domain'] = [('link_id', '=', self.id)]
        return action

    @api.multi
    def action_visit_page(self):
        return {
            'name': _("Visit Webpage"),
            'type': 'ir.actions.act_url',
            'url': self.url,
            'target': 'new',
        }

    @api.model
    def recent_links(self, filter, limit):
        if filter == 'newest':
            return self.search_read([], order='create_date DESC, id DESC', limit=limit)
        elif filter == 'most-clicked':
            return self.search_read([('count', '!=', 0)], order='count DESC', limit=limit)
        elif filter == 'recently-used':
            return self.search_read([('count', '!=', 0)], order='write_date DESC, id DESC', limit=limit)
        else:
            return {'Error': "This filter doesn't exist."}

    @api.model
    def get_url_from_code(self, code):
        code_rec = self.env['link.tracker.code'].sudo().search([('code', '=', code)])

        if not code_rec:
            return None

        return code_rec.link_id.redirected_url

    _sql_constraints = [
        ('url_utms_uniq', 'unique (url, campaign_id, medium_id, source_id)', 'The URL and the UTM combination must be unique')
    ]


class LinkTrackerCode(models.Model):
    _name = "link.tracker.code"
    _description = "Link Tracker Code"

    code = fields.Char(string='Short URL Code', required=True, store=True)
    link_id = fields.Many2one('link.tracker', 'Link', required=True, ondelete='cascade')

    _sql_constraints = [
        ('code', 'unique( code )', 'Code must be unique.')
    ]

    @api.model
    def get_random_code_string(self):
        size = 3
        while True:
            code_proposition = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(size))

            if self.search([('code', '=', code_proposition)]):
                size += 1
            else:
                return code_proposition


class LinkTrackerClick(models.Model):
    _name = "link.tracker.click"
    _rec_name = "link_id"
    _description = "Link Tracker Click"

    link_id = fields.Many2one('link.tracker', 'Link', required=True, ondelete='cascade')
    ip = fields.Char(string='Internet Protocol')
    country_id = fields.Many2one('res.country', 'Country')

    def _prepare_click_values_from_route(self, **route_values):
        click_values = dict((fname, route_values[fname]) for fname in self._fields if fname in route_values)
        if not click_values.get('country_id') and route_values.get('country_code'):
            click_values['country_id'] = self.env['res.country'].search([('code', '=', route_values['country_code'])], limit=1).id
        return click_values

    @api.model
    def add_click(self, code, **route_values):
        """ Main API to add a click on a link. """
        tracker_code = self.env['link.tracker.code'].search([('code', '=', code)])
        if not tracker_code:
            return None

        ip = route_values.get('ip', False)
        existing = self.search_count(['&', ('link_id', '=', tracker_code.link_id.id), ('ip', '=', ip)])
        if existing:
            return None

        route_values['link_id'] = tracker_code.link_id.id
        click_values = self._prepare_click_values_from_route(**route_values)

        return self.create(click_values)
