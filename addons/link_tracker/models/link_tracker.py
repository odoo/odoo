# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
import requests
import string

from lxml import html
from werkzeug import urls

from odoo import tools, models, fields, api, _

URL_MAX_SIZE = 10 * 1024 * 1024


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
    _order="count DESC"
    _inherit = ["utm.mixin"]

    # URL info
    url = fields.Char(string='Target URL', required=True)
    absolute_url = fields.Char("Absolute URL", compute="_compute_absolute_url")
    short_url = fields.Char(string='Tracked URL', compute='_compute_short_url')
    redirected_url = fields.Char(string='Redirected URL', compute='_compute_redirected_url')
    short_url_host = fields.Char(string='Host of the short URL', compute='_compute_short_url_host')
    title = fields.Char(string='Page Title', store=True)
    label = fields.Char(string='Button label')
    # Tracking
    link_code_ids = fields.One2many('link.tracker.code', 'link_id', string='Codes')
    code = fields.Char(string='Short URL code', compute='_compute_code')
    link_click_ids = fields.One2many('link.tracker.click', 'link_id', string='Clicks')
    count = fields.Integer(string='Number of Clicks', compute='_compute_count', store=True)

    @api.depends("url")
    def _compute_absolute_url(self):
        web_base_url = urls.url_parse(self.env['ir.config_parameter'].sudo().get_param('web.base.url'))
        for tracker in self:
            url = urls.url_parse(tracker.url)
            if url.scheme:
                tracker.absolute_url = tracker.url
            else:
                tracker.absolute_url = web_base_url.join(url).to_url()

    @api.depends('link_click_ids.link_id')
    def _compute_count(self):
        if self.ids:
            clicks_data = self.env['link.tracker.click'].read_group(
                [('link_id', 'in', self.ids)],
                ['link_id'],
                ['link_id']
            )
            mapped_data = {m['link_id'][0]: m['link_id_count'] for m in clicks_data}
        else:
            mapped_data = dict()
        for tracker in self:
            tracker.count = mapped_data.get(tracker.id, 0)

    @api.depends('code')
    def _compute_short_url(self):
        for tracker in self:
            tracker.short_url = urls.url_join(tracker.short_url_host, '%(code)s' % {'code': tracker.code})

    def _compute_short_url_host(self):
        for tracker in self:
            base_url = tracker.get_base_url()
            tracker.short_url_host = urls.url_join(base_url, '/r/')

    def _compute_code(self):
        for tracker in self:
            record = self.env['link.tracker.code'].search([('link_id', '=', tracker.id)], limit=1, order='id DESC')
            tracker.code = record.code

    @api.depends('url')
    def _compute_redirected_url(self):
        """Compute the URL to which we will redirect the user.

        By default, add UTM values as GET parameters. But if the system parameter
        `link_tracker.no_external_tracking` is set, we add the UTM values in the URL
        *only* for URLs that redirect to the local website (base URL).
        """
        no_external_tracking = self.env['ir.config_parameter'].sudo().get_param('link_tracker.no_external_tracking')

        for tracker in self:
            base_domain = urls.url_parse(tracker.get_base_url()).netloc
            parsed = urls.url_parse(tracker.url)
            if no_external_tracking and parsed.netloc and parsed.netloc != base_domain:
                tracker.redirected_url = parsed.to_url()
                continue

            utms = {}
            for key, field_name, cook in self.env['utm.mixin'].tracking_fields():
                field = self._fields[field_name]
                attr = getattr(tracker, field_name)
                if field.type == 'many2one':
                    attr = attr.name
                if attr:
                    utms[key] = attr
            utms.update(parsed.decode_query())
            tracker.redirected_url = parsed.replace(query=urls.url_encode(utms)).to_url()

    @api.model
    @api.depends('url')
    def _get_title_from_url(self, url):
        try:
            head = requests.head(url, timeout=5)
            if (
                    int(head.headers.get('Content-Length', 0)) > URL_MAX_SIZE
                    or
                    'text/html' not in head.headers.get('Content-Type', 'text/html')
            ):
                return url
            # HTML parser can work with a part of page, so ask server to limit downloading to 50 KB
            page = requests.get(url, timeout=5, headers={"range": "bytes=0-50000"})
            p = html.fromstring(page.text.encode('utf-8'), parser=html.HTMLParser(encoding='utf-8'))
            title = p.find('.//title').text
        except:
            title = url

        return title

    @api.model
    def create(self, vals):
        create_vals = vals.copy()

        if 'url' not in create_vals:
            raise ValueError('URL field required')
        else:
            create_vals['url'] = tools.validate_url(vals['url'])

        search_domain = [
            (fname, '=', value)
            for fname, value in create_vals.items()
            if fname in ['url', 'campaign_id', 'medium_id', 'source_id']
        ]

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
        raise NotImplementedError('Moved on mail.render.mixin')

    def _convert_links_text(self, body, vals, blacklist=None):
        raise NotImplementedError('Moved on mail.render.mixin')

    def action_view_statistics(self):
        action = self.env['ir.actions.act_window']._for_xml_id('link_tracker.link_tracker_click_action_statistics')
        action['domain'] = [('link_id', '=', self.id)]
        action['context'] = dict(self._context, create=False)
        return action

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
    _rec_name = 'code'

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

    campaign_id = fields.Many2one(
        'utm.campaign', 'UTM Campaign',
        related="link_id.campaign_id", store=True)
    link_id = fields.Many2one(
        'link.tracker', 'Link',
        index=True, required=True, ondelete='cascade')
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
