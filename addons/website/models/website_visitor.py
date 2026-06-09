# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import _, SQL
from odoo.tools.date_utils import all_timezones
from odoo.tools.misc import _format_time_ago
from odoo.http import request


class WebsiteTrack(models.Model):
    _name = 'website.track'
    _description = 'Visited Page'
    _order = 'visit_datetime DESC, id DESC'
    _log_access = False

    visitor_id = fields.Many2one('website.visitor', ondelete="cascade", index=True, required=True, readonly=True)
    url = fields.Text('Url', index=True)
    visit_datetime = fields.Datetime('Visit Date', default=fields.Datetime.now, required=True, readonly=True)
    res_model = fields.Char(string="Model Name")
    res_id = fields.Many2oneReference(model_field='res_model', string="Record")


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
    country_id = fields.Many2one('res.country', 'Country', readonly=True, index='btree_not_null')
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
    page_count = fields.Integer('# Visited Pages', compute="_compute_page_statistics", help="Number of distinct tracked pages visited")
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
            if not visitor.id:
                visitor.partner_id = visitor._origin.partner_id
                continue
            # If the access_token is not a 32 length hexa string, it means that
            # the visitor is linked to a logged in user, in which case its
            # partner_id is used instead as the token.
            partner_id = len(visitor.access_token) != 32 and int(visitor.access_token)
            visitor.partner_id = self.env['res.partner'].browse(partner_id)

    @api.depends('partner_id.email_normalized', 'partner_id.phone')
    def _compute_email_phone(self):
        results = self.env['res.partner'].search_read(
            [('id', 'in', self.partner_id.ids)],
            ['id', 'email_normalized', 'phone'],
        )
        mapped_data = {
            result['id']: {
                'email_normalized': result['email_normalized'],
                'phone': result['phone']
            } for result in results
        }

        for visitor in self:
            visitor.email = mapped_data.get(visitor.partner_id.id, {}).get('email_normalized')
            visitor.mobile = mapped_data.get(visitor.partner_id.id, {}).get('phone')

    @api.depends('website_track_ids')
    def _compute_page_statistics(self):
        domain = Domain('visitor_id', 'in', self.ids) & Domain('url', '!=', False)

        results = self.env['website.track']._read_group(
            domain=domain,
            groupby=['visitor_id', 'res_model', 'res_id'],
            aggregates=['__count'],
        )
        mapped_data = {}
        for visitor, res_model, res_id, count in results:
            stats = mapped_data.setdefault(visitor.id, {'ids': set(), 'count': 0})
            stats['count'] += count
            if res_model == 'website.page' and res_id:
                stats['ids'].add(res_id)

        for visitor in self:
            stats = mapped_data.get(visitor.id, {'ids': [], 'count': 0})
            visitor.page_ids = [(6, 0, list(stats['ids']))]
            visitor.visitor_page_count = stats['count']
            visitor.page_count = len(stats['ids'])

    def _get_visitor_statistics(self, rel_model, track_field='res_id', extra_domain=None):
        """
        Return visitor statistics from `website.track`.

        :param track_field: Field on `website.track` to aggregate
        :param rel_model: Filter on res_model
        :param extra_domain: Additional domain filters
        :return: dict mapping visitor.id to
                    {'ids': [record ids], 'count': total_visits}
        """
        # Build base domain
        domain = Domain('visitor_id', 'in', self.ids) & Domain('res_model', '=', rel_model)

        groupby = ['visitor_id']
        if extra_domain:
            domain &= Domain(extra_domain)

        Track = self.env['website.track']
        results = Track._read_group(
            domain=domain,
            groupby=groupby,
            aggregates=[f'{track_field}:array_agg', '__count'],
        )
        return {
            visitor.id: {
                'ids': ids or [],
                'count': count or 0,
            }
            for visitor, ids, count in results
        }

    def _search_page_ids(self, operator, value):
        return [
            ('website_track_ids.res_model', '=', 'website.page'),
            ('website_track_ids.res_id.name', operator, value),
        ]

    @api.depends('website_track_ids.res_id', 'website_track_ids.res_model')
    def _compute_last_visited_page_id(self):
        domain = Domain('visitor_id', 'in', self.ids) & Domain('res_model', '=', 'website.page') & Domain('res_id', '!=', False)

        results = self.env['website.track']._read_group(
            domain=domain,
            groupby=['visitor_id', 'res_id'],
            order='visit_datetime:max')
        mapped_data = dict(results)
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
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
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

    def _upsert_visitor(self, token_or_partner_id, website_id, lang_id=None, country_code=None, timezone=None, url=None, **kwargs):
        """ Based on the given `access_token`, either create or return the
        related visitor if exists, through a single raw SQL UPSERT Query.

        It will also create a tracking record if requested, in the same query.

        :param token_or_partner_id: token (or partner id) to be used to identify the visitor
        :param website_id: every visit is typically for a particular website
        :param lang_id: visitors language id
        :param country_code: visitors country code
        :param timezone: visitors time zone
        :param url: optional url to create a track record at the same time
        :param kwargs: additional values to include in the track record, including
            res_model/res_id for the visited resource
        :return: a tuple containing the visitor id and the upsert result (either
            `inserted` or `updated).
        """
        create_values = {
            'access_token': token_or_partner_id,
            'lang_id': lang_id,
            'country_code': country_code,
            'website_id': website_id,
            'timezone': timezone,
            'write_uid': self.env.uid,
            'create_uid': self.env.uid,
            # If the access_token is not a 32 length hexa string, it means that the
            # visitor is linked to a logged in user, in which case its partner_id is
            # used instead as the token.
            'partner_id': None if len(str(token_or_partner_id)) == 32 else token_or_partner_id,
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
                write_date = excluded.write_date,
                visit_count = CASE WHEN website_visitor.last_connection_datetime < NOW() AT TIME ZONE 'UTC' - INTERVAL '8 hours'
                                    THEN website_visitor.visit_count + 1
                                    ELSE website_visitor.visit_count
                                END
            RETURNING id, CASE WHEN create_date = write_date THEN 'inserted' ELSE 'updated' END AS upsert
        """, **create_values)

        if url:
            cols_extra, vals_extra = self._get_additional_track_query_parts(**kwargs)
            query = SQL("""
                WITH visitor AS (
                    %(query)s
                ), track AS (
                    INSERT INTO website_track (visitor_id, url, visit_datetime %(cols_extra)s)
                    SELECT id, %(url)s, now() at time zone 'UTC' %(vals_extra)s FROM visitor
                )
                SELECT id, upsert from visitor;
                """,
                query=query,
                url=url,
                cols_extra=cols_extra,
                vals_extra=vals_extra,
            )

        [result] = self.env.execute_query(query)
        return result

    def _get_additional_track_query_parts(self, **kwargs):
        TrackModel = self.env['website.track']
        cols, vals = [], []
        for fname, val in kwargs.items():
            if fname in TrackModel._fields and val:
                cols.append(SQL(", %s", SQL.identifier(fname)))
                vals.append(SQL(", %s", val))
        return SQL().join(cols), SQL().join(vals)

    def visitor_view_action_button(self):
        """Return an action to display tracking records for this visitor.

        Reads model name and title from context, and opens a list/graph view
        of `website.track` filtered by the current visitor and model.

        :return: action dict to open tracking views
        """
        self.ensure_one()
        context = self.env.context
        if not context.get('model_name'):
            raise UserError(_("Model information is required to view visitor tracking details."))
        return {
            'type': 'ir.actions.act_window',
            'name': context.get('title', _('Views History')),
            'res_model': 'website.track',
            'view_mode': 'list',
            'views': [
                (self.env.ref("website.website_visitor_track_view_base_list").id, 'list'),
            ],
            'domain': [
                ('visitor_id', '=', self.id),
                ('res_model', '=', context.get('model_name')),
            ],
        }

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

    def _cron_unlink_old_visitors(self, batch_size=1000):
        """ Unlink inactive visitors (see '_inactive_visitors_domain' for
        details).

        Visitors were previously archived but we came to the conclusion that
        archived visitors have very little value and bloat the database for no
        reason. """
        domain = self._inactive_visitors_domain()
        visitors = self.env['website.visitor'].sudo().search(domain, limit=batch_size)
        visitors.unlink()
        self.env['ir.cron']._commit_progress(
            processed=len(visitors),
            remaining=0 if len(visitors) < batch_size else visitors.search_count(domain),
        )

    def _inactive_visitors_domain(self):
        """ This method defines the domain of visitors that can be cleaned. By
        default visitors not linked to any partner and not active for
        'website.visitor.live.days' days (default being 60) are considered as
        inactive.

        This method is meant to be overridden by sub-modules to further refine
        inactivity conditions. """

        delay_days = self.env['ir.config_parameter'].sudo().get_int('website.visitor.live.days') or 60
        deadline = datetime.now() - timedelta(days=delay_days)
        return Domain('last_connection_datetime', '<', deadline) & Domain('partner_id', '=', False)

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
        if tz in all_timezones:
            return tz
        elif not self.env.user._is_public():
            return self.env.user.tz
        else:
            return None
