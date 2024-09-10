# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

import hashlib
import pytz
import threading

from odoo import fields, models, api, _
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import UserError
from odoo.tools import split_every, SQL
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


class WebsiteVisitor(models.Model):
    _name = 'website.visitor'
    _description = 'Website Visitor'
    _order = 'id DESC'

    def _get_access_token(self):
        """ Either the user's partner.id or a hash. """
        if not request:
            raise ValueError("Visitors can only be created through the frontend.")

        if not request.env.user._is_public():
            return request.env.user.partner_id.id

        msg = repr((
            request.httprequest.remote_addr,
            request.httprequest.environ.get('HTTP_USER_AGENT'),
            request.session.sid,
        )).encode('utf-8')
        # Keep same length (32) as before, it will ease the migration without
        # any real downside
        return hashlib.sha1(msg).hexdigest()[:32]

    name = fields.Char('Name', related='partner_id.name')
    access_token = fields.Char(required=True, default=_get_access_token, copy=False)
    website_id = fields.Many2one('website', "Website", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Contact", help="Partner of the last logged in user.", compute='_compute_partner_id', store=True, index='btree_not_null')
    partner_image = fields.Binary(related='partner_id.image_1920')

    # localisation and info
    country_id = fields.Many2one('res.country', 'Country', readonly=True)
    country_flag = fields.Char(related="country_id.image_url", string="Country Flag")
    lang_id = fields.Many2one('res.lang', string='Language', help="Language from the website when visitor has been created")
    timezone = fields.Selection(_tz_get, string='Timezone')
    email = fields.Char(string='Email', compute='_compute_email_phone', compute_sudo=True)
    mobile = fields.Char(string='Mobile', compute='_compute_email_phone', compute_sudo=True)

    # Visit fields
    visit_count = fields.Integer('# Visits', default=1, readonly=True, help="A new visit is considered if last connection was more than 8 hours ago.")
    website_track_ids = fields.One2many('website.track', 'visitor_id', string='Visited Pages History', readonly=True)
    visitor_page_count = fields.Integer('Page Views', compute="_compute_page_statistics", help="Total number of visits on tracked pages")
    page_ids = fields.Many2many('website.page', string="Visited Pages", compute="_compute_page_statistics", groups="website.group_website_designer", search="_search_page_ids")
    page_count = fields.Integer('# Visited Pages', compute="_compute_page_statistics", help="Total number of tracked page visited")
    last_visited_page_id = fields.Many2one('website.page', string="Last Visited Page", compute="_compute_last_visited_page_id")

    # Time fields
    create_date = fields.Datetime('First Connection', readonly=True)
    last_connection_datetime = fields.Datetime('Last Connection', default=fields.Datetime.now, help="Last page view date", readonly=True)
    time_since_last_action = fields.Char('Last action', compute="_compute_time_statistics", help='Time since last page view. E.g.: 2 minutes ago')
    is_connected = fields.Boolean('Is connected?', compute='_compute_time_statistics', help='A visitor is considered as connected if his last page view was within the last 5 minutes.')

    _access_token_unique = models.Constraint(
        'unique(access_token)',
        'Access token should be unique.',
    )

    @api.depends('partner_id')
    def _compute_display_name(self):
        for record in self:
            # Accessing name of partner through sudo to avoid infringing
            # record rule if partner belongs to another company.
            record.display_name = record.partner_id.sudo().name or _('Website Visitor #%s', record.id)

    @api.depends('access_token')
    def _compute_partner_id(self):
        # The browse in the loop is fine, there is no SQL Query on partner here
        for visitor in self:
            # If the access_token is not a 32 length hexa string, it means that
            # the visitor is linked to a logged in user, in which case its
            # partner_id is used instead as the token.
            partner_id = len(visitor.access_token) != 32 and int(visitor.access_token)
            visitor.partner_id = self.env['res.partner'].browse(partner_id)

    @api.depends('partner_id.email_normalized', 'partner_id.mobile', 'partner_id.phone')
    def _compute_email_phone(self):
        results = self.env['res.partner'].search_read(
            [('id', 'in', self.partner_id.ids)],
            ['id', 'email_normalized', 'mobile', 'phone'],
        )
        mapped_data = {
            result['id']: {
                'email_normalized': result['email_normalized'],
                'mobile': result['mobile'] if result['mobile'] else result['phone']
            } for result in results
        }

        for visitor in self:
            visitor.email = mapped_data.get(visitor.partner_id.id, {}).get('email_normalized')
            visitor.mobile = mapped_data.get(visitor.partner_id.id, {}).get('mobile')

    @api.depends('website_track_ids')
    def _compute_page_statistics(self):
        results = self.env['website.track']._read_group(
            [('visitor_id', 'in', self.ids), ('url', '!=', False)], ['visitor_id', 'page_id'], ['__count'])
        mapped_data = {}
        for visitor, page, count in results:
            visitor_info = mapped_data.get(visitor.id, {'page_count': 0, 'visitor_page_count': 0, 'page_ids': set()})
            visitor_info['visitor_page_count'] += count
            visitor_info['page_count'] += 1
            if page:
                visitor_info['page_ids'].add(page.id)
            mapped_data[visitor.id] = visitor_info

        for visitor in self:
            visitor_info = mapped_data.get(visitor.id, {'page_count': 0, 'visitor_page_count': 0, 'page_ids': set()})
            visitor.page_ids = [(6, 0, visitor_info['page_ids'])]
            visitor.visitor_page_count = visitor_info['visitor_page_count']
            visitor.page_count = visitor_info['page_count']

    def _search_page_ids(self, operator, value):
        if operator not in ('like', 'ilike', 'not like', 'not ilike', '=like', '=ilike', '=', '!='):
            raise ValueError(_('This operator is not supported'))
        return [('website_track_ids.page_id.name', operator, value)]

    @api.depends('website_track_ids.page_id')
    def _compute_last_visited_page_id(self):
        results = self.env['website.track']._read_group(
            [('visitor_id', 'in', self.ids), ('page_id', '!=', False)],
            ['visitor_id', 'page_id'],
            order='visit_datetime:max')
        mapped_data = {visitor.id: page.id for visitor, page in results}
        for visitor in self:
            visitor.last_visited_page_id = mapped_data.get(visitor.id, False)

    @api.depends('last_connection_datetime')
    def _compute_time_statistics(self):
        for visitor in self:
            visitor.time_since_last_action = _format_time_ago(self.env, (datetime.now() - visitor.last_connection_datetime))
            visitor.is_connected = (datetime.now() - visitor.last_connection_datetime) < timedelta(minutes=5)

    def _check_for_message_composer(self):
        """ Purpose of this method is to actualize visitor model prior to contacting
        him. Used notably for inheritance purpose, when dealing with leads that
        could update the visitor model. """
        return bool(self.partner_id and self.partner_id.email)

    def _prepare_message_composer_context(self):
        return {
            'default_model': 'res.partner',
            'default_res_ids': self.partner_id.ids,
            'default_partner_ids': [self.partner_id.id],
        }

    def action_send_mail(self):
        self.ensure_one()
        if not self._check_for_message_composer():
            raise UserError(_("There are no contact and/or no email linked to this visitor."))
        visitor_composer_ctx = self._prepare_message_composer_context()
        compose_form = self.env.ref('mail.email_compose_message_wizard_form')
        compose_ctx = dict(
            default_composition_mode='comment',
        )
        compose_ctx.update(**visitor_composer_ctx)
        return {
            'name': _('Contact Visitor'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': compose_ctx,
        }

    def _upsert_visitor(self, access_token, force_track_values=None):
        """ Based on the given `access_token`, either create or return the
        related visitor if exists, through a single raw SQL UPSERT Query.

        It will also create a tracking record if requested, in the same query.

        :param access_token: token to be used to upsert the visitor
        :param force_track_values: an optional dict to create a track at the
            same time.
        :return: a tuple containing the visitor id and the upsert result (either
            `inserted` or `updated).
        """
        create_values = {
            'access_token': access_token,
            'lang_id': request.lang.id,
            # Note that it's possible for the GEOIP database to return a country
            # code which is unknown in Odoo
            'country_code': request.geoip.get('country_code'),
            'website_id': request.website.id,
            'timezone': self._get_visitor_timezone() or None,
            'write_uid': self.env.uid,
            'create_uid': self.env.uid,
            # If the access_token is not a 32 length hexa string, it means that the
            # visitor is linked to a logged in user, in which case its partner_id is
            # used instead as the token.
            'partner_id': None if len(str(access_token)) == 32 else access_token,
        }
        query = SQL("""
            INSERT INTO website_visitor (
                partner_id, access_token, last_connection_datetime, visit_count, lang_id,
                website_id, timezone, write_uid, create_uid, write_date, create_date, country_id)
            VALUES (
                %(partner_id)s, %(access_token)s, now() at time zone 'UTC', 1, %(lang_id)s,
                %(website_id)s, %(timezone)s, %(create_uid)s, %(write_uid)s,
                now() at time zone 'UTC', now() at time zone 'UTC', (
                    SELECT id FROM res_country WHERE code = %(country_code)s
                )
            )
            ON CONFLICT (access_token)
            DO UPDATE SET
                last_connection_datetime=excluded.last_connection_datetime,
                visit_count = CASE WHEN website_visitor.last_connection_datetime < NOW() AT TIME ZONE 'UTC' - INTERVAL '8 hours'
                                    THEN website_visitor.visit_count + 1
                                    ELSE website_visitor.visit_count
                                END
            RETURNING id, CASE WHEN create_date = now() at time zone 'UTC' THEN 'inserted' ELSE 'updated' END AS upsert
        """, **create_values)

        if force_track_values:
            query = SQL("""
                WITH visitor AS (
                    %(query)s, %(url)s AS url, %(page_id)s AS page_id
                ), track AS (
                    INSERT INTO website_track (visitor_id, url, page_id, visit_datetime)
                    SELECT id, url, page_id::integer, now() at time zone 'UTC' FROM visitor
                )
                SELECT id, upsert from visitor;
                """,
                query=query,
                url=force_track_values['url'],
                page_id=force_track_values.get('page_id'),
            )

        [result] = self.env.execute_query(query)
        return result

    def _get_visitor_from_request(self, force_create=False, force_track_values=None):
        """ Return the visitor as sudo from the request.

        :param force_create: force a visitor creation if no visitor exists
        :param force_track_values: an optional dict to create a track at the
            same time.
        :return: the website visitor if exists or forced, empty recordset
            otherwise.
        """

        # This function can be called in json with mobile app.
        # In case of mobile app, no uid is set on the jsonRequest env.
        # In case of multi db, _env is None on request, and request.env unbound.
        if not (request and request.env and request.env.uid):
            return None

        access_token = self._get_access_token()

        if force_create:
            visitor_id, _ = self._upsert_visitor(access_token, force_track_values)
            return self.env['website.visitor'].sudo().browse(visitor_id)

        visitor = self.env['website.visitor'].sudo().search([('access_token', '=', access_token)])

        if not force_create and not self.env.cr.readonly and visitor and not visitor.timezone:
            tz = self._get_visitor_timezone()
            if tz:
                visitor._update_visitor_timezone(tz)

        return visitor

    def _handle_webpage_dispatch(self, website_page):
        """ Create a website.visitor if the http request object is a tracked
        website.page or a tracked ir.ui.view.
        Since this method is only called on tracked elements, the
        last_connection_datetime might not be accurate as the visitor could have
        been visiting only untracked page during his last visit."""

        url = request.httprequest.url
        website_track_values = {'url': url}
        if website_page:
            website_track_values['page_id'] = website_page.id

        self._get_visitor_from_request(force_create=True, force_track_values=website_track_values)

    def _add_tracking(self, domain, website_track_values):
        """ Add the track and update the visitor"""
        domain = expression.AND([domain, [('visitor_id', '=', self.id)]])
        last_view = self.env['website.track'].sudo().search(domain, limit=1)
        if not last_view or last_view.visit_datetime < datetime.now() - timedelta(minutes=30):
            website_track_values['visitor_id'] = self.id
            self.env['website.track'].create(website_track_values)
        self._update_visitor_last_visit()

    def _merge_visitor(self, target):
        """ Merge an anonymous visitor data to a partner visitor then unlink
        that anonymous visitor.
        Purpose is to try to aggregate as much sub-records (tracked pages,
        leads, ...) as possible.
        It is especially useful to aggregate data from the same user on
        different devices.

        This method is meant to be overridden for other modules to merge their
        own anonymous visitor data to the partner visitor before unlink.

        This method is only called after the user logs in.

        :param target: main visitor, target of link process;
        """
        if not target.partner_id:
            raise ValueError("The `target` visitor should be linked to a partner.")
        self.website_track_ids.visitor_id = target.id
        self.unlink()

    def _cron_unlink_old_visitors(self, batch_size=1000, limit=None):
        """ Unlink inactive visitors (see '_inactive_visitors_domain' for
        details).

        Visitors were previously archived but we came to the conclusion that
        archived visitors have very little value and bloat the database for no
        reason. """
        auto_commit = not getattr(threading.current_thread(), 'testing', False)
        visitor_model = self.env['website.visitor']
        visitor_ids = visitor_model.sudo().search(self._inactive_visitors_domain(), limit=limit).ids
        visitor_done = 0
        for inactive_visitors_batch in split_every(
            batch_size,
            visitor_ids,
            visitor_model.browse,
        ):
            inactive_visitors_batch.unlink()
            visitor_done += len(inactive_visitors_batch)
            if auto_commit:
                self.env['ir.cron']._notify_progress(done=visitor_done, remaining=len(visitor_ids) - visitor_done)
                self.env.cr.commit()
        self.env['ir.cron']._notify_progress(done=visitor_done, remaining=len(visitor_ids) - visitor_done)

    def _inactive_visitors_domain(self):
        """ This method defines the domain of visitors that can be cleaned. By
        default visitors not linked to any partner and not active for
        'website.visitor.live.days' days (default being 60) are considered as
        inactive.

        This method is meant to be overridden by sub-modules to further refine
        inactivity conditions. """

        delay_days = int(self.env['ir.config_parameter'].sudo().get_param('website.visitor.live.days', 60))
        deadline = datetime.now() - timedelta(days=delay_days)
        return [('last_connection_datetime', '<', deadline), ('partner_id', '=', False)]

    def _update_visitor_timezone(self, timezone):
        """ We need to do this part here to avoid concurrent updates error. """
        query = """
            UPDATE website_visitor
            SET timezone = %s
            WHERE id IN (
                SELECT id FROM website_visitor WHERE id = %s
                FOR NO KEY UPDATE SKIP LOCKED
            )
        """
        self.env.cr.execute(query, (timezone, self.id))

    def _update_visitor_last_visit(self):
        date_now = datetime.now()
        query = "UPDATE website_visitor SET "
        if self.last_connection_datetime < (date_now - timedelta(hours=8)):
            query += "visit_count = visit_count + 1,"
        query += """
            last_connection_datetime = %s
            WHERE id IN (
                SELECT id FROM website_visitor WHERE id = %s
                FOR NO KEY UPDATE SKIP LOCKED
            )
        """
        self.env.cr.execute(query, (date_now, self.id), log_exceptions=False)

    def _get_visitor_timezone(self):
        tz = request.cookies.get('tz') if request else None
        if tz in pytz.all_timezones:
            return tz
        elif not self.env.user._is_public():
            return self.env.user.tz
        else:
            return None
