# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
import requests
import string

from lxml import html
from werkzeug import urls

from odoo import tools, models, fields, api, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.addons.mail.tools import link_preview


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
    # UTMs - enforcing the fact that we want to 'set null' when relation is unlinked
    campaign_id = fields.Many2one(ondelete='set null')
    medium_id = fields.Many2one(ondelete='set null')
    source_id = fields.Many2one(ondelete='set null')

    @api.depends("url")
    def _compute_absolute_url(self):
        for tracker in self:
            url = urls.url_parse(tracker.url)
            if url.scheme:
                tracker.absolute_url = tracker.url
            else:
                tracker.absolute_url = tracker.get_base_url().join(url).to_url()

    @api.depends('link_click_ids.link_id')
    def _compute_count(self):
        clicks_data = self.env['link.tracker.click']._read_group(
            [('link_id', 'in', self.ids)],
            ['link_id'],
            ['__count'],
        )
        mapped_data = {link.id: count for link, count in clicks_data}
        for tracker in self:
            tracker.count = mapped_data.get(tracker.id, 0)

    @api.depends('code')
    def _compute_short_url(self):
        for tracker in self:
            tracker.short_url = urls.url_join(tracker.short_url_host, '%(code)s' % {'code': tracker.code})

    def _compute_short_url_host(self):
        for tracker in self:
            tracker.short_url_host = tracker.get_base_url() + '/r/'

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
                attr = tracker[field_name]
                if field.type == 'many2one':
                    attr = attr.name
                if attr:
                    utms[key] = attr
            utms.update(parsed.decode_query())
            tracker.redirected_url = parsed.replace(query=urls.url_encode(utms)).to_url()

    @api.model
    @api.depends('url')
    def _get_title_from_url(self, url):
        preview = link_preview.get_link_preview_from_url(url)
        if preview and preview.get('og_title'):
            return preview['og_title']
        return url

    @api.constrains('url', 'campaign_id', 'medium_id', 'source_id')
    def _check_unicity(self):
        """Check that the link trackers are unique."""
        # build a query to fetch all needed link trackers at once
        search_query = expression.OR([
            expression.AND([
                [('url', '=', tracker.url)],
                [('campaign_id', '=', tracker.campaign_id.id)],
                [('medium_id', '=', tracker.medium_id.id)],
                [('source_id', '=', tracker.source_id.id)],
            ])
            for tracker in self
        ])

        # Can not be implemented with a SQL constraint because we want to care about null values.
        all_link_trackers = self.search(search_query)

        # check for unicity
        for tracker in self:
            if all_link_trackers.filtered(
                lambda l: l.url == tracker.url
                and l.campaign_id == tracker.campaign_id
                and l.medium_id == tracker.medium_id
                and l.source_id == tracker.source_id
            ) != tracker:
                raise UserError(_(
                    'Link Tracker values (URL, campaign, medium and source) must be unique (%s, %s, %s, %s).',
                    tracker.url,
                    tracker.campaign_id.name,
                    tracker.medium_id.name,
                    tracker.source_id.name,
                ))

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [vals.copy() for vals in vals_list]
        for vals in vals_list:
            if 'url' not in vals:
                raise ValueError(_('Creating a Link Tracker without URL is not possible'))

            if vals['url'].startswith(('?', '#')):
                raise UserError(_("%r is not a valid link, links cannot redirect to the current page.", vals['url']))
            vals['url'] = tools.validate_url(vals['url'])

            if not vals.get('title'):
                vals['title'] = self._get_title_from_url(vals['url'])

            # Prevent the UTMs to be set by the values of UTM cookies
            for (__, fname, __) in self.env['utm.mixin'].tracking_fields():
                if fname not in vals:
                    vals[fname] = False

        links = super(LinkTracker, self).create(vals_list)

        link_tracker_codes = self.env['link.tracker.code']._get_random_code_strings(len(vals_list))

        self.env['link.tracker.code'].sudo().create([
            {
                'code': code,
                'link_id': link.id,
            } for link, code in zip(links, link_tracker_codes)
        ])

        return links

    @api.model
    def search_or_create(self, vals):
        if 'url' not in vals:
            raise ValueError(_('Creating a Link Tracker without URL is not possible'))
        if vals['url'].startswith(('?', '#')):
            raise UserError(_("%r is not a valid link, links cannot redirect to the current page.", vals['url']))
        vals['url'] = tools.validate_url(vals['url'])

        search_domain = [
            (fname, '=', value)
            for fname, value in vals.items()
            if fname in ['url', 'campaign_id', 'medium_id', 'source_id']
        ]
        result = self.search(search_domain, limit=1)

        if result:
            return result

        return self.create(vals)

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
    def _get_random_code_strings(self, n=1):
        size = 3
        while True:
            code_propositions = [
                ''.join(random.choices(string.ascii_letters + string.digits, k=size))
                for __ in range(n)
            ]

            if len(set(code_propositions)) != n or self.search([('code', 'in', code_propositions)]):
                size += 1
            else:
                return code_propositions


class LinkTrackerClick(models.Model):
    _name = "link.tracker.click"
    _rec_name = "link_id"
    _description = "Link Tracker Click"

    campaign_id = fields.Many2one(
        'utm.campaign', 'UTM Campaign',
        related="link_id.campaign_id", store=True, ondelete="set null")
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

        route_values['link_id'] = tracker_code.link_id.id
        click_values = self._prepare_click_values_from_route(**route_values)

        return self.create(click_values)
