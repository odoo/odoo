# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from hashlib import sha256
import hmac

from odoo import fields, models, api, _
from odoo.tools.misc import _consteq, _format_time_ago
from odoo.http import request


class WebsitVisitorPage(models.Model):
    _name = 'website.visitor.page'
    _description = 'Visited Pages'
    _order = 'visit_datetime ASC'
    _log_access = False

    visitor_id = fields.Many2one('website.visitor', ondelete="cascade", index=True, required=True, readonly=True)
    page_id = fields.Many2one('website.page', index=True, ondelete='cascade', readonly=True)
    visit_datetime = fields.Datetime('Visit Date', default=fields.Datetime.now, required=True, readonly=True)


class WebsiteVisitor(models.Model):
    _name = 'website.visitor'
    _description = 'Website Visitor'
    _order = 'last_connection_datetime DESC'

    name = fields.Char('Name', default=_('Website Visitor'))
    active = fields.Boolean('Active', default=True)
    website_id = fields.Many2one('website', "Website", readonly=True)
    user_partner_id = fields.Many2one('res.partner', string="Linked Partner", help="Partner of the last logged in user.")
    create_date = fields.Datetime('First connection date', readonly=True)
    last_connection_datetime = fields.Datetime('Last Connection', help="Last page view date", readonly=True)
    country_id = fields.Many2one('res.country', 'Country', readonly=True)
    country_flag = fields.Binary(related="country_id.image", string="Country Flag")
    lang_id = fields.Many2one('res.lang', string='Language', help="Language from the website when visitor has been created")
    visit_count = fields.Integer('Number of visits', default=1, readonly=True, help="A new visit is considered if last connection was more than 8 hours ago.")
    visitor_page_ids = fields.One2many('website.visitor.page', 'visitor_id', string='Visited Pages History', readonly=True)
    visitor_page_count = fields.Integer('Page Views', compute="_compute_page_statistics")
    page_ids = fields.Many2many('website.page', string="Visited Pages", compute="_compute_page_statistics", store=True)
    page_count = fields.Integer('# Visited Pages', compute="_compute_page_statistics")
    time_since_last_action = fields.Char('Last action', compute="_compute_time_statistics", help='Time since last page view. E.g.: 2 minutes ago')
    is_connected = fields.Boolean('Is connected ?', compute='_compute_time_statistics', help='A visitor is considered as connected if his last page view was within the last 5 minutes.')

    @api.depends('visitor_page_ids')
    def _compute_page_statistics(self):
        results = self.env['website.visitor.page'].read_group(
            [('visitor_id', 'in', self.ids)], ['visitor_id', 'page_id'], ['visitor_id', 'page_id'], lazy=False)
        mapped_data = {}
        for result in results:
            visitor_info = mapped_data.get(result['visitor_id'][0], {'page_count': 0, 'page_ids': set()})
            visitor_info['page_count'] += result['__count']
            visitor_info['page_ids'].add(result['page_id'][0])
            mapped_data[result['visitor_id'][0]] = visitor_info

        for visitor in self:
            visitor_info = mapped_data.get(visitor.id, {'page_ids': [], 'page_count': 0})

            visitor.page_ids = [(6, 0, visitor_info['page_ids'])]
            visitor.visitor_page_count = visitor_info['page_count']
            visitor.page_count = len(visitor_info['page_ids'])

    @api.depends('last_connection_datetime')
    def _compute_time_statistics(self):
        results = self.env['website.visitor'].search_read([('id', 'in', self.ids)], ['id', 'last_connection_datetime'])
        mapped_data = {result['id']: result['last_connection_datetime'] for result in results}

        for visitor in self:
            last_connection_date = mapped_data[visitor.id]
            visitor.time_since_last_action = _format_time_ago(self.env, (datetime.now() - last_connection_date))
            visitor.is_connected = (datetime.now() - last_connection_date) < timedelta(minutes=5)

    def _get_visitor_sign(self):
        return {visitor.id: "%d-%s" % (visitor.id, self._get_visitor_hash(visitor.id)) for visitor in self}

    @api.model
    def _get_visitor_hash(self, visitor_id):
        db_secret = request.env['ir.config_parameter'].sudo().get_param('database.secret')
        return hmac.new(str(visitor_id).encode('utf-8'), db_secret.encode('utf-8'), sha256).hexdigest()

    def _get_visitor_from_request(self):
        if not request:
            return None
        visitor = self.env['website.visitor']
        cookie_content = request.httprequest.cookies.get('visitor_id')
        if cookie_content and '-' in cookie_content:
            visitor_id, visitor_hash = cookie_content.split('-', 1)
            if _consteq(visitor_hash, self._get_visitor_hash(visitor_id)):
                return visitor.sudo().with_context(active_test=False).search([('id', '=', visitor_id)])  # search to avoid having to call exists()
        return visitor

    def _handle_webpage_dispatch(self, response, website_page):
        if website_page:
            # get visitor only if page tracked. Done here to avoid having to do it multiple times in case of override.
            visitor_sudo = self._get_visitor_from_request() if website_page.is_tracked else False
            self._handle_website_page_visit(response, website_page, visitor_sudo)

    def _handle_website_page_visit(self, response, website_page, visitor_sudo):
        """ Called on dispatch. This will create a website.visitor if the http request object
        is a tracked website page. Only on tracked page to avoid having too much operations done on every page
        or other http requests.
        Note: The side effect is that the last_connection_datetime is updated ONLY on tracked pages."""
        if website_page.is_tracked:
            if not visitor_sudo:
                # If visitor does not exist
                visitor_sudo = self._create_visitor(website_page.id)
                sign = visitor_sudo._get_visitor_sign().get(visitor_sudo.id)
                response.set_cookie('visitor_id', sign)
            else:
                # Add page even if already in visitor_page_ids as checks on relations are done in many2many write method
                vals = {
                    'last_connection_datetime': datetime.now(),
                    'visitor_page_ids': [(0, 0, {'page_id': website_page.id, 'visit_datetime': datetime.now()})],
                }
                if visitor_sudo.last_connection_datetime < (datetime.now() - timedelta(hours=8)):
                    vals['visit_count'] = visitor_sudo.visit_count + 1
                if not visitor_sudo.active:
                    vals['active'] = True
                visitor_sudo.write(vals)

    def _create_visitor(self, website_page_id=False):
        country_code = request.session.get('geoip', {}).get('country_code', False)
        country_id = request.env['res.country'].sudo().search([('code', '=', country_code)], limit=1).id if country_code else False
        lang_id = request.env['res.lang'].sudo().search([('code', '=', request.lang)], limit=1).id
        vals = {
            'last_connection_datetime': datetime.now(),
            'lang_id': lang_id,
            'country_id': country_id,
            'website_id': request.website.id
        }
        if not self.env.user._is_public():
            vals['user_partner_id'] = self.env.user.partner_id.id
        if website_page_id:
            vals['visitor_page_ids'] = [(0, 0, {'page_id': website_page_id, 'visit_datetime': datetime.now()})]
        # Set signed visitor id in cookie
        return self.sudo().create(vals)

    def _cron_archive_visitors(self):
        one_week_ago = datetime.now() - timedelta(days=7)
        visitors_to_archive = self.env['website.visitor'].sudo().search([('last_connection_datetime', '<', one_week_ago)])
        visitors_to_archive.write({'active': False})
