# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
import uuid

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools.misc import _format_time_ago
from odoo.http import request
from odoo.osv import expression


class WebsiteTrack(models.Model):
    _name = 'website.track'
    _description = 'Visited Pages'
    _order = 'visit_datetime DESC'
    _log_access = False

    visitor_id = fields.Many2one('website.visitor', ondelete="cascade", index=True, required=True, readonly=True)
    page_id = fields.Many2one('website.page', index=True, ondelete='cascade', readonly=True)
    url = fields.Text('Url', index=True)
    visit_datetime = fields.Datetime('Visit Date', default=fields.Datetime.now, required=True, readonly=True)


class VisitorLastConnection(models.Model):
    _name = 'website.visitor.lastconnection'
    _description = 'temporary table for Visitor'

    visitor_id = fields.Many2one('website.visitor', ondelete="cascade", index=True, required=True, readonly=True)
    connection_datetime = fields.Datetime(default=fields.Datetime.now, required=True, readonly=True)


class WebsiteVisitor(models.Model):
    _name = 'website.visitor'
    _description = 'Website Visitor'
    _order = 'create_date DESC'

    name = fields.Char('Name', default=_('Website Visitor'))
    access_token = fields.Char(required=True, default=lambda x: uuid.uuid4().hex, index=True, copy=False, groups='base.group_website_publisher')
    active = fields.Boolean('Active', default=True)
    website_id = fields.Many2one('website', "Website", readonly=True)
    user_partner_id = fields.Many2one('res.partner', string="Linked Partner", help="Partner of the last logged in user.")

    # localisation and info
    country_id = fields.Many2one('res.country', 'Country', readonly=True)
    country_flag = fields.Binary(related="country_id.image", string="Country Flag")
    lang_id = fields.Many2one('res.lang', string='Language', help="Language from the website when visitor has been created")
    email = fields.Char(string='Email', compute='_compute_email_phone')
    mobile = fields.Char(string='Mobile Phone', compute='_compute_email_phone')

    # Visit fields
    visit_count = fields.Integer('Number of visits', default=1, readonly=True, help="A new visit is considered if last connection was more than 24 hours ago.")
    website_track_ids = fields.One2many('website.track', 'visitor_id', string='Visited Pages History', readonly=True)
    visitor_page_count = fields.Integer('Page Views', compute="_compute_page_statistics", help="Total number of visits on tracked pages")
    page_ids = fields.Many2many('website.page', string="Visited Pages", compute="_compute_page_statistics")
    page_count = fields.Integer('# Visited Pages', compute="_compute_page_statistics", help="Total number of tracked page visited")

    # Time fields
    create_date = fields.Datetime('First connection date', readonly=True)
    last_connection_datetime = fields.Datetime('Last Connection', compute="_compute_time_statistics", help="Last page view date", search='_search_last_connection', readonly=True)
    last_connections_ids = fields.One2many('website.visitor.lastconnection', 'visitor_id', readonly=True)
    time_since_last_action = fields.Char('Last action', compute="_compute_time_statistics", help='Time since last page view. E.g.: 2 minutes ago')
    is_connected = fields.Boolean('Is connected ?', compute='_compute_time_statistics', help='A visitor is considered as connected if his last page view was within the last 5 minutes.')

    @api.depends('name')
    def name_get(self):
        ret_list = []
        for record in self:
            name = '%s #%d' % (record.name, record.id)
            ret_list.append((record.id, name))
        return ret_list

    @api.model
    def _search_last_connection(self, operator, value):
        assert operator in expression.TERM_OPERATORS
        self.env['website.visitor.lastconnection'].flush(['visitor_id'])
        query = """
            SELECT v.visitor_id
            FROM website_visitor_lastconnection v
            WHERE v.connection_datetime %s %%s
            GROUP BY v.visitor_id, v.connection_datetime
            ORDER BY v.connection_datetime
        """ % (operator,)
        return [('id', 'inselect', (query, [value]))]

    @api.depends('user_partner_id.email_normalized', 'user_partner_id.mobile')
    def _compute_email_phone(self):
        results = self.env['res.partner'].search_read(
            [('id', 'in', self.user_partner_id.ids)],
            ['id', 'email_normalized', 'mobile'],
        )
        mapped_data = {
            result['id']: {
                'email_normalized': result['email_normalized'],
                'mobile': result['mobile']
            } for result in results
        }

        for visitor in self:
            visitor.email = mapped_data.get(visitor.user_partner_id.id, {}).get('email_normalized')
            visitor.mobile = mapped_data.get(visitor.user_partner_id.id, {}).get('mobile')

    @api.depends('website_track_ids')
    def _compute_page_statistics(self):
        results = self.env['website.track'].read_group(
            [('visitor_id', 'in', self.ids), ('url', '!=', False)], ['visitor_id', 'page_id', 'url'], ['visitor_id', 'page_id', 'url'], lazy=False)
        mapped_data = {}
        for result in results:
            visitor_info = mapped_data.get(result['visitor_id'][0], {'page_count': 0, 'visitor_page_count': 0, 'page_ids': set()})
            visitor_info['visitor_page_count'] += result['__count']
            visitor_info['page_count'] += 1
            if result['page_id']:
                visitor_info['page_ids'].add(result['page_id'][0])
            mapped_data[result['visitor_id'][0]] = visitor_info

        for visitor in self:
            visitor_info = mapped_data.get(visitor.id, {'page_ids': [], 'page_count': 0})
            visitor.page_ids = [(6, 0, visitor_info['page_ids'])]
            visitor.visitor_page_count = visitor_info['visitor_page_count']
            visitor.page_count = visitor_info['page_count']

    @api.depends('last_connections_ids')
    def _compute_time_statistics(self):
        results = self.env['website.visitor.lastconnection'].read_group([('visitor_id', 'in', self.ids)], ['visitor_id', 'connection_datetime:max'], ['visitor_id'])
        mapped_data = {result['visitor_id'][0]: result['connection_datetime'] for result in results}
        for visitor in self:
            last_connection_datetime = mapped_data.get(visitor.id, False)
            if last_connection_datetime:
                visitor.last_connection_datetime = last_connection_datetime
                visitor.time_since_last_action = _format_time_ago(self.env, (datetime.now() - last_connection_datetime))
                visitor.is_connected = (datetime.now() - last_connection_datetime) < timedelta(minutes=5)

    def _prepare_visitor_send_mail_values(self):
        if self.user_partner_id.email:
            return {
                'res_model': 'res.partner',
                'res_id': self.user_partner_id.id,
                'partner_ids': [self.user_partner_id.id],
            }
        return {}

    def action_send_mail(self):
        self.ensure_one()
        visitor_mail_values = self._prepare_visitor_send_mail_values()
        if not visitor_mail_values:
            raise UserError(_("There is no email linked this visitor."))
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model=visitor_mail_values.get('res_model'),
            default_res_id=visitor_mail_values.get('res_id'),
            default_use_template=False,
            default_partner_ids=[(6, 0, visitor_mail_values.get('partner_ids'))],
            default_composition_mode='comment',
            default_reply_to=self.env.user.partner_id.email,
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def _get_visitor_from_request(self, with_previous_visitors=False):
        if not request:
            return None
        if with_previous_visitors and not request.env.user._is_public():
            partner_id = request.env.user.partner_id
            # Retrieve all the previous partner's visitors to have full history of his last products viewed.
            return request.env['website.visitor'].sudo().with_context(active_test=False).search([('user_partner_id', '=', partner_id.id)])
        else:
            visitor = self.env['website.visitor']
            access_token = request.httprequest.cookies.get('visitor_id')
            if access_token:
                visitor = visitor.sudo().with_context(active_test=False).search([('access_token', '=', access_token)])
            return visitor

    def _handle_webpage_dispatch(self, response, website_page):
        # get visitor. Done here to avoid having to do it multiple times in case of override.
        visitor_sudo = self._get_visitor_from_request()
        self._handle_website_page_visit(response, website_page, visitor_sudo)

    def _handle_website_page_visit(self, response, website_page, visitor_sudo):
        """ Called on dispatch. This will create a website.visitor if the http request object
        is a tracked website page or a tracked view. Only on tracked elements to avoid having
        too much operations done on every page or other http requests.
        Note: The side effect is that the last_connection_datetime is updated ONLY on tracked elements."""
        url = request.httprequest.url
        website_track_values = {
            'url': url,
            'visit_datetime': datetime.now(),
        }
        if website_page:
            website_track_values['page_id'] = website_page.id
            domain = [('page_id', '=', website_page.id)]
        else:
            domain = [('url', '=', url)]
        if not visitor_sudo:
            visitor_sudo = self._create_visitor(website_track_values)
            expiration_date = datetime.now() + timedelta(days=365)
            response.set_cookie('visitor_id', visitor_sudo.access_token, expires=expiration_date)
        else:
            visitor_sudo._add_tracking(domain, website_track_values)
            if visitor_sudo.lang_id.id != request.lang.id:
                visitor_sudo.write({'lang_id': request.lang.id})

    def _add_tracking(self, domain, website_track_values):
        """ Update the visitor when a website_track is added"""
        domain = expression.AND([domain, [('visitor_id', '=', self.id)]])
        last_view = self.env['website.track'].sudo().search(domain, limit=1)
        if not last_view or last_view.visit_datetime < datetime.now() - timedelta(minutes=30):
            website_track_values['visitor_id'] = self.id
            self.env['website.track'].create(website_track_values)
        self.env['website.visitor.lastconnection'].create({
            'visitor_id': self.id,
            'connection_datetime': website_track_values['visit_datetime']
        })

    def _create_visitor(self, website_track_values=None):
        """ Create a visitor and add a track to it if website_track_values is set."""
        country_code = request.session.get('geoip', {}).get('country_code', False)
        country_id = request.env['res.country'].sudo().search([('code', '=', country_code)], limit=1).id if country_code else False
        vals = {
            'lang_id': request.lang.id,
            'country_id': country_id,
            'website_id': request.website.id,
            'last_connections_ids': [(0, 0, {'connection_datetime': website_track_values['visit_datetime'] or datetime.now()})],
        }
        if not self.env.user._is_public():
            vals['user_partner_id'] = self.env.user.partner_id.id
            vals['name'] = self.env.user.partner_id.name
        if website_track_values:
            vals['website_track_ids'] = [(0, 0, website_track_values)]
        return self.sudo().create(vals)

    def _cron_archive_visitors(self):
        self.flush(['visit_count'])
        yesterday = datetime.now() - timedelta(days=1)
        query = """
            UPDATE website_visitor
            SET visit_count = visit_count + 1
            WHERE id in (
                SELECT visitor_id
                FROM website_visitor_lastconnection
                GROUP BY visitor_id
                HAVING COUNT(*) > 1)
        """
        self.env.cr.execute(query, [yesterday])

        query = """
            DELETE FROM website_visitor_lastconnection
            WHERE (visitor_id, connection_datetime) not in (
               SELECT v.visitor_id, max(connection_datetime)
               FROM website_visitor_lastconnection v
               GROUP BY v.visitor_id)
        """
        self.env.cr.execute(query, [])

        one_week_ago = datetime.now() - timedelta(days=7)
        visitors_to_archive = self.env['website.visitor'].sudo().search([('last_connection_datetime', '<', one_week_ago)])
        visitors_to_archive.write({'active': False})
