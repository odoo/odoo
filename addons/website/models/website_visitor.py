# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.http import request
from datetime import datetime, timedelta
from hashlib import md5


class WebsiteVisitor(models.Model):
    _name = 'website.visitor'
    _description = 'Website Visitor'
    _order = 'last_connection_date DESC'

    name = fields.Char('Name', default='Website Visitor')
    website_id = fields.Many2one('website', "Website")
    partner_ids = fields.Many2many('res.partner')
    partner_count = fields.Integer('# Partners', compute="_compute_partner_count")
    create_date = fields.Datetime('First connexion date', default=fields.Datetime.now)
    last_connection_date = fields.Datetime('Last Connection', help="Last page view date")
    country_id = fields.Many2one('res.country', 'Country', readonly=True)
    country_flag = fields.Binary(related="country_id.image", string="Country Flag")
    lang_id = fields.Many2one('res.lang', string='Language', help="Language from the website when visitor has been created")
    visit_count = fields.Integer('Number of visits', default=1, help="If last visit was more than 8 hours ago, the new connection is considered as a new visit. Else, it is considered as same visit.")
    page_ids = fields.One2many('website.visitor.page', 'visitor_id', string='Visited Pages History')
    page_view_count = fields.Integer('Page Views', compute="_compute_page_view_count")
    unique_page_ids = fields.Many2many('website.page', string="Visited Pages", compute="_compute_unique_page_ids", store=True)
    time_last_action = fields.Float('Time since last action', compute="_compute_time_last_action", help='Time since last page view in seconds')
    is_connected = fields.Boolean('Is connected ?', compute='_compute_is_connected', help='A visitor is considered as connected if his last page view was within the last 5 minutes.')
    # Maybe not necessary, only used for visitor - lead - customer views (filtered on type)
    # but could check directly on domain.
    type = fields.Selection([
        ('visitor', 'Visitor'),
        ('customer', 'Customer'),
    ], string="Type", default='visitor', compute="_compute_type", store=True)

    @api.depends('partner_ids')
    def _compute_partner_count(self):
        for visitor in self:
            visitor.partner_count = len(visitor.partner_ids)

    @api.depends('page_ids')
    def _compute_page_view_count(self):
        for visitor in self:
            visitor.page_view_count = len(visitor.page_ids)

    @api.depends('page_ids')
    def _compute_unique_page_ids(self):
        for visitor in self:
            unique_page_ids = list(set(visitor.page_ids.page_id.ids))
            visitor.unique_page_ids = [(6, 0, unique_page_ids)]

    @api.depends('last_connection_date')
    def _compute_time_last_action(self):
        for visitor in self:
            visitor.time_last_action = (datetime.now() - visitor.last_connection_date).total_seconds()/60

    @api.depends('last_connection_date')
    def _compute_is_connected(self):
        for visitor in self:
            visitor.is_connected = (datetime.now() - visitor.last_connection_date) < timedelta(minutes=5)

    @api.depends('partner_ids')
    def _compute_type(self):
        for visitor in self:
            visitor.type = 'customer' if visitor.partner_ids else 'visitor'

    def _encode(self, visitor_id):
        md5_visitor_id = md5(b"%d%s" % (visitor_id, self._get_key().encode('ascii'))).hexdigest()
        return "%d-%s" % (visitor_id, md5_visitor_id)

    def _decode(self):
        # opens the cookie, verifies the signature of the visitor
        # returns visitor if the verification passes and None otherwise
        if request:  # To pass the tests (as in tests, users are authenticated BEFORE making requests)
            cookie_content = request.httprequest.cookies.get('visitor_id')
            if cookie_content and '-' in cookie_content:
                visitor_id, md5_visitor_id = cookie_content.split('-', 1)
                expected_encryped_visitor_id = md5(("%s%s" % (visitor_id, self._get_key())).encode('utf-8')).hexdigest()
                if md5_visitor_id == expected_encryped_visitor_id:
                    visitor = int(visitor_id)
                    return visitor if visitor else None
        return None

    def _get_key(self):
        return self.env['ir.config_parameter'].sudo().get_param('database.secret')

    def _handle_visitor_response(self, response):
        """ Called on dispatch. This will create a website.visitor if the http request object
        is a tracked website page. This is to avoid having too much operations done on every page
        or other http requests."""
        # If request is ok
        website_page = response.qcontext['main_object']
        # check if page is tracked
        # we create/update the visitor only on tracked pages to avoid to much requests
        # (if we did this on every visited website_page)
        # But the side effect is that the last_connection_date is updated ONLY on tracked pages.
        if website_page and website_page.track:
            visitor = self.env['website.visitor'].browse(self._decode())
            vals = {
                'last_connection_date': datetime.now(),
            }
            if not visitor.exists():
                # If visitor does not exist
                country_code = request.session.geoip and request.session.geoip.get('country_code')
                country_id = request.env['res.country'].sudo().search([('code', '=', country_code)], limit=1).id
                lang_id = request.env['res.lang'].sudo().search([('code', '=', request.lang)], limit=1).id
                vals.update({
                    'lang_id': lang_id,
                    'country_id': country_id,
                    'page_ids': [(0, 0, {'page_id': website_page.id, 'visit_date': datetime.now()})],
                    'website_id': request.website.id
                })
                # Set signed visitor id in cookie
                visitor_sudo = self.sudo().create(vals)
                sign = self._encode(visitor_sudo.id)
                response.set_cookie('visitor_id', sign)
            else:
                visitor_sudo = visitor.sudo()
                # Would need to round on current day midnight and check if today is another day
                if visitor_sudo.last_connection_date < (datetime.now() - timedelta(seconds=10)):
                    vals['visit_count'] = visitor_sudo.visit_count + 1
                # Add page even if already in page_ids as checks on relations are done in many2many write method
                vals['page_ids'] = [(0, 0, {'page_id': website_page.id, 'visit_date': datetime.now()})]
                visitor_sudo.write(vals)
        return response


class WebsitVisitorPage(models.Model):
    _name = 'website.visitor.page'
    _description = 'Page visited by a visitor'
    _table = 'website_visitor_page'
    _order = 'visit_date DESC'
    _log_access = False

    visitor_id = fields.Many2one('website.visitor', ondelete="cascade", index=True, required=True)
    page_id = fields.Many2one('website.page', index=True, ondelete='cascade')
    visit_date = fields.Datetime('Visit Date', default=fields.Datetime.now, required=True)
