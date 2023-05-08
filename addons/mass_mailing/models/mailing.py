# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import logging
import lxml
import random
import re
import threading
import werkzeug.urls
from ast import literal_eval
from dateutil.relativedelta import relativedelta
from markupsafe import Markup
from werkzeug.urls import url_join

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

_logger = logging.getLogger(__name__)

# Syntax of the data URL Scheme: https://tools.ietf.org/html/rfc2397#section-3
# Used to find inline images
image_re = re.compile(r"data:(image/[A-Za-z]+);base64,(.*)")


class MassMailing(models.Model):
    """ Mass Mailing models the sending of emails to a list of recipients for a mass mailing campaign."""
    _name = 'mailing.mailing'
    _description = 'Mass Mailing'
    _inherit = ['mail.thread',
                'mail.activity.mixin',
                'mail.render.mixin',
                'utm.source.mixin'
    ]
    _order = 'calendar_date DESC'
    _rec_name = "subject"

    @api.model
    def default_get(self, fields_list):
        vals = super(MassMailing, self).default_get(fields_list)

        # field sent by the calendar view when clicking on a date block
        # we use it to setup the scheduled date of the created mailing.mailing
        default_calendar_date = self.env.context.get('default_calendar_date')
        if default_calendar_date and ('schedule_type' in fields_list and 'schedule_date' in fields_list) \
           and fields.Datetime.from_string(default_calendar_date) > fields.Datetime.now():
            vals.update({
                'schedule_type': 'scheduled',
                'schedule_date': default_calendar_date
            })

        if 'contact_list_ids' in fields_list and not vals.get('contact_list_ids') and vals.get('mailing_model_id'):
            if vals.get('mailing_model_id') == self.env['ir.model']._get('mailing.list').id:
                mailing_list = self.env['mailing.list'].search([], limit=2)
                if len(mailing_list) == 1:
                    vals['contact_list_ids'] = [(6, 0, [mailing_list.id])]
        return vals

    @api.model
    def _get_default_mail_server_id(self):
        server_id = self.env['ir.config_parameter'].sudo().get_param('mass_mailing.mail_server_id')
        try:
            server_id = literal_eval(server_id) if server_id else False
            return self.env['ir.mail_server'].search([('id', '=', server_id)]).id
        except ValueError:
            return False

    active = fields.Boolean(default=True, tracking=True)
    subject = fields.Char(
        'Subject', required=True, translate=False)
    preview = fields.Char(
        'Preview', translate=False,
        help='Catchy preview sentence that encourages recipients to open this email.\n'
             'In most inboxes, this is displayed next to the subject.\n'
             'Keep it empty if you prefer the first characters of your email content to appear instead.')
    email_from = fields.Char(
        string='Send From',
        compute='_compute_email_from', readonly=False, required=True, store=True,
        default=lambda self: self.env.user.email_formatted)
    favorite = fields.Boolean('Favorite', copy=False, tracking=True)
    favorite_date = fields.Datetime(
        'Favorite Date',
        compute='_compute_favorite_date', store=True,
        copy=False,
        help='When this mailing was added in the favorites')
    sent_date = fields.Datetime(string='Sent Date', copy=False)
    schedule_type = fields.Selection(
        [('now', 'Send now'), ('scheduled', 'Send on')],
        string='Schedule', default='now',
        readonly=True, required=True,
        states={'draft': [('readonly', False)], 'in_queue': [('readonly', False)]})
    schedule_date = fields.Datetime(
        string='Scheduled for',
        compute='_compute_schedule_date', readonly=True, store=True,
        copy=True, tracking=True,
        states={'draft': [('readonly', False)], 'in_queue': [('readonly', False)]})
    calendar_date = fields.Datetime(
        'Calendar Date',
        compute='_compute_calendar_date', store=True,
        copy=False,
        help="Date at which the mailing was or will be sent.")
    # don't translate 'body_arch', the translations are only on 'body_html'
    body_arch = fields.Html(string='Body', translate=False, sanitize=False)
    body_html = fields.Html(string='Body converted to be sent by mail', render_engine='qweb', sanitize=False)

   # used to determine if the mail body is empty
    is_body_empty = fields.Boolean(compute="_compute_is_body_empty")
    attachment_ids = fields.Many2many(
        'ir.attachment', 'mass_mailing_ir_attachments_rel',
        'mass_mailing_id', 'attachment_id', string='Attachments')
    keep_archives = fields.Boolean(string='Keep Archives')
    campaign_id = fields.Many2one('utm.campaign', string='UTM Campaign', index=True, ondelete='set null')
    medium_id = fields.Many2one(
        'utm.medium', string='Medium',
        compute='_compute_medium_id', readonly=False, store=True,
        ondelete='restrict',
        help="UTM Medium: delivery method (email, sms, ...)")
    state = fields.Selection(
        [('draft', 'Draft'), ('in_queue', 'In Queue'),
         ('sending', 'Sending'), ('done', 'Sent')],
        string='Status',
        default='draft', required=True,
        copy=False, tracking=True,
        group_expand='_group_expand_states')
    color = fields.Integer(string='Color Index')
    user_id = fields.Many2one(
        'res.users', string='Responsible',
        tracking=True,
        default=lambda self: self.env.user)
    # mailing options
    mailing_type = fields.Selection([('mail', 'Email')], string="Mailing Type", default="mail", required=True)
    mailing_type_description = fields.Char('Mailing Type Description', compute="_compute_mailing_type_description")
    reply_to_mode = fields.Selection(
        [('update', 'Recipient Followers'), ('new', 'Specified Email Address')],
        string='Reply-To Mode',
        compute='_compute_reply_to_mode', readonly=False, store=True,
        help='Thread: replies go to target document. Email: replies are routed to a given email.')
    reply_to = fields.Char(
        string='Reply To',
        compute='_compute_reply_to', readonly=False, store=True,
        help='Preferred Reply-To Address')
    # recipients
    mailing_model_real = fields.Char(
        string='Recipients Real Model', compute='_compute_mailing_model_real')
    mailing_model_id = fields.Many2one(
        'ir.model', string='Recipients Model',
        ondelete='cascade', required=True,
        domain=[('is_mailing_enabled', '=', True)],
        default=lambda self: self.env.ref('mass_mailing.model_mailing_list').id)
    mailing_model_name = fields.Char(
        string='Recipients Model Name',
        related='mailing_model_id.model', readonly=True, related_sudo=True)
    mailing_domain = fields.Char(
        string='Domain',
        compute='_compute_mailing_domain', readonly=False, store=True)
    mail_server_available = fields.Boolean(
        compute='_compute_mail_server_available',
        help="Technical field used to know if the user has activated the outgoing mail server option in the settings")
    mail_server_id = fields.Many2one('ir.mail_server', string='Mail Server',
        default=_get_default_mail_server_id,
        help="Use a specific mail server in priority. Otherwise Odoo relies on the first outgoing mail server available (based on their sequencing) as it does for normal mails.")
    contact_list_ids = fields.Many2many('mailing.list', 'mail_mass_mailing_list_rel', string='Mailing Lists')
    # Mailing Filter
    mailing_filter_id = fields.Many2one(
        'mailing.filter', string='Favorite Filter',
        compute='_compute_mailing_filter_id', readonly=False, store=True,
        domain="[('mailing_model_name', '=', mailing_model_name)]")
    mailing_filter_domain = fields.Char('Favorite filter domain', related='mailing_filter_id.mailing_domain')
    mailing_filter_count = fields.Integer('# Favorite Filters', compute='_compute_mailing_filter_count')
    # A/B Testing
    ab_testing_completed = fields.Boolean(related='campaign_id.ab_testing_completed', store=True)
    ab_testing_description = fields.Html('A/B Testing Description', compute="_compute_ab_testing_description")
    ab_testing_enabled = fields.Boolean(
        string='Allow A/B Testing', default=False,
        help='If checked, recipients will be mailed only once for the whole campaign. '
             'This lets you send different mailings to randomly selected recipients and test '
             'the effectiveness of the mailings, without causing duplicate messages.')
    ab_testing_mailings_count = fields.Integer(related="campaign_id.ab_testing_mailings_count")
    ab_testing_pc = fields.Integer(
        string='A/B Testing percentage',
        default=10,
        help='Percentage of the contacts that will be mailed. Recipients will be chosen randomly.')
    ab_testing_schedule_datetime = fields.Datetime(
        related="campaign_id.ab_testing_schedule_datetime", readonly=False,
        default=lambda self: fields.Datetime.now() + relativedelta(days=1))
    ab_testing_winner_selection = fields.Selection(
        related="campaign_id.ab_testing_winner_selection", readonly=False,
        default="opened_ratio",
        copy=True)
    kpi_mail_required = fields.Boolean('KPI mail required', copy=False)
    # statistics data
    mailing_trace_ids = fields.One2many('mailing.trace', 'mass_mailing_id', string='Emails Statistics')
    total = fields.Integer(compute="_compute_total")
    scheduled = fields.Integer(compute="_compute_statistics")
    expected = fields.Integer(compute="_compute_statistics")
    canceled = fields.Integer(compute="_compute_statistics")
    sent = fields.Integer(compute="_compute_statistics")
    delivered = fields.Integer(compute="_compute_statistics")
    opened = fields.Integer(compute="_compute_statistics")
    clicked = fields.Integer(compute="_compute_statistics")
    replied = fields.Integer(compute="_compute_statistics")
    bounced = fields.Integer(compute="_compute_statistics")
    failed = fields.Integer(compute="_compute_statistics")
    received_ratio = fields.Integer(compute="_compute_statistics", string='Received Ratio')
    opened_ratio = fields.Integer(compute="_compute_statistics", string='Opened Ratio')
    replied_ratio = fields.Integer(compute="_compute_statistics", string='Replied Ratio')
    bounced_ratio = fields.Integer(compute="_compute_statistics", string='Bounced Ratio')
    clicks_ratio = fields.Integer(compute="_compute_clicks_ratio", string="Number of Clicks")
    next_departure = fields.Datetime(compute="_compute_next_departure", string='Scheduled date')
    # UX
    warning_message = fields.Char(
        'Warning Message', compute='_compute_warning_message',
        help='Warning message displayed in the mailing form view')

    _sql_constraints = [(
        'percentage_valid',
        'CHECK(ab_testing_pc >= 0 AND ab_testing_pc <= 100)',
        'The A/B Testing Percentage needs to be between 0 and 100%'
    )]

    @api.constrains('mailing_model_id', 'mailing_filter_id')
    def _check_mailing_filter_model(self):
        """Check that if the favorite filter is set, it must contain the same recipient model as mailing"""
        for mailing in self:
            if mailing.mailing_filter_id and mailing.mailing_model_id != mailing.mailing_filter_id.mailing_model_id:
                raise ValidationError(
                    _("The saved filter targets different recipients and is incompatible with this mailing.")
                )

    @api.depends('mail_server_id')
    def _compute_email_from(self):
        user_email = self.env.user.email_formatted
        notification_email = self.env['ir.mail_server']._get_default_from_address()

        for mailing in self:
            server = mailing.mail_server_id
            if not server:
                mailing.email_from = mailing.email_from or user_email
            elif mailing.email_from and server._match_from_filter(mailing.email_from, server.from_filter):
                mailing.email_from = mailing.email_from
            elif server._match_from_filter(user_email, server.from_filter):
                mailing.email_from = user_email
            elif server._match_from_filter(notification_email, server.from_filter):
                mailing.email_from = notification_email
            else:
                mailing.email_from = mailing.email_from or user_email

    @api.depends('favorite')
    def _compute_favorite_date(self):
        favorited = self.filtered('favorite')
        (self - favorited).favorite_date = False
        favorited.filtered(lambda mailing: not mailing.favorite_date).favorite_date = fields.Datetime.now()

    def _compute_total(self):
        for mass_mailing in self:
            total = self.env[mass_mailing.mailing_model_real].search_count(mass_mailing._parse_mailing_domain())
            if total and mass_mailing.ab_testing_enabled and mass_mailing.ab_testing_pc < 100:
                total = max(int(total / 100.0 * mass_mailing.ab_testing_pc), 1)
            mass_mailing.total = total

    def _compute_clicks_ratio(self):
        self.env.cr.execute("""
            SELECT COUNT(DISTINCT(stats.id)) AS nb_mails, COUNT(DISTINCT(clicks.mailing_trace_id)) AS nb_clicks, stats.mass_mailing_id AS id
            FROM mailing_trace AS stats
            LEFT OUTER JOIN link_tracker_click AS clicks ON clicks.mailing_trace_id = stats.id
            WHERE stats.mass_mailing_id IN %s
            GROUP BY stats.mass_mailing_id
        """, [tuple(self.ids) or (None,)])
        mass_mailing_data = self.env.cr.dictfetchall()
        mapped_data = dict([(m['id'], 100 * m['nb_clicks'] / m['nb_mails']) for m in mass_mailing_data])
        for mass_mailing in self:
            mass_mailing.clicks_ratio = mapped_data.get(mass_mailing.id, 0)

    def _compute_statistics(self):
        """ Compute statistics of the mass mailing """
        for key in (
            'scheduled', 'expected', 'canceled', 'sent', 'delivered', 'opened',
            'clicked', 'replied', 'bounced', 'failed', 'received_ratio',
            'opened_ratio', 'replied_ratio', 'bounced_ratio',
        ):
            self[key] = False
        if not self.ids:
            return
        # ensure traces are sent to db
        self.env['mailing.trace'].flush_model()
        self.env['mailing.mailing'].flush_model()
        self.env.cr.execute("""
            SELECT
                m.id as mailing_id,
                COUNT(s.id) AS expected,
                COUNT(s.sent_datetime) AS sent,
                COUNT(s.trace_status) FILTER (WHERE s.trace_status = 'outgoing') AS scheduled,
                COUNT(s.trace_status) FILTER (WHERE s.trace_status = 'cancel') AS canceled,
                COUNT(s.trace_status) FILTER (WHERE s.trace_status in ('sent', 'open', 'reply')) AS delivered,
                COUNT(s.trace_status) FILTER (WHERE s.trace_status in ('open', 'reply')) AS opened,
                COUNT(s.links_click_datetime) AS clicked,
                COUNT(s.trace_status) FILTER (WHERE s.trace_status = 'reply') AS replied,
                COUNT(s.trace_status) FILTER (WHERE s.trace_status = 'bounce') AS bounced,
                COUNT(s.trace_status) FILTER (WHERE s.trace_status = 'error') AS failed
            FROM
                mailing_trace s
            RIGHT JOIN
                mailing_mailing m
                ON (m.id = s.mass_mailing_id)
            WHERE
                m.id IN %s
            GROUP BY
                m.id
        """, (tuple(self.ids), ))
        for row in self.env.cr.dictfetchall():
            total = (row['expected'] - row['canceled']) or 1
            row['received_ratio'] = 100.0 * row['delivered'] / total
            row['opened_ratio'] = 100.0 * row['opened'] / total
            row['replied_ratio'] = 100.0 * row['replied'] / total
            row['bounced_ratio'] = 100.0 * row['bounced'] / total
            self.browse(row.pop('mailing_id')).update(row)

    def _compute_next_departure(self):
        # Schedule_date should only be False if schedule_type = "now" or
        # mass_mailing is canceled.
        # A cron.trigger is created when mailing is put "in queue"
        # so we can reasonably expect that the cron worker will
        # execute this based on the cron.trigger's call_at which should
        # be now() when clicking "Send" or schedule_date if scheduled

        for mass_mailing in self:
            if mass_mailing.schedule_date:
                # max in case the user schedules a date in the past
                mass_mailing.next_departure = max(mass_mailing.schedule_date, fields.datetime.now())
            else:
                mass_mailing.next_departure = fields.datetime.now()

    @api.depends('email_from', 'mail_server_id')
    def _compute_warning_message(self):
        for mailing in self:
            mail_server = mailing.mail_server_id
            if mail_server and not mail_server._match_from_filter(mailing.email_from, mail_server.from_filter):
                mailing.warning_message = _(
                    'This email from can not be used with this mail server.\n'
                    'Your emails might be marked as spam on the mail clients.'
                )
            else:
                mailing.warning_message = False

    @api.depends('mailing_type')
    def _compute_medium_id(self):
        for mailing in self:
            if mailing.mailing_type == 'mail' and not mailing.medium_id:
                mailing.medium_id = self.env.ref('utm.utm_medium_email').id

    @api.depends('mailing_model_id')
    def _compute_reply_to_mode(self):
        """ For main models not really using chatter to gather answers (contacts
        and mailing contacts), set reply-to as email-based. Otherwise answers
        by default go on the original discussion thread (business document). Note
        that mailing_model being mailing.list means contacting mailing.contact
        (see mailing_model_name versus mailing_model_real). """
        for mailing in self:
            if mailing.mailing_model_id.model in ['res.partner', 'mailing.list', 'mailing.contact']:
                mailing.reply_to_mode = 'new'
            else:
                mailing.reply_to_mode = 'update'

    @api.depends('reply_to_mode')
    def _compute_reply_to(self):
        for mailing in self:
            if mailing.reply_to_mode == 'new' and not mailing.reply_to:
                mailing.reply_to = self.env.user.email_formatted
            elif mailing.reply_to_mode == 'update':
                mailing.reply_to = False

    @api.depends('mailing_model_id', 'mailing_domain')
    def _compute_mailing_filter_count(self):
        filter_data = self.env['mailing.filter']._read_group([
            ('mailing_model_id', 'in', self.mailing_model_id.ids)
        ], ['mailing_model_id'], ['mailing_model_id'])
        mapped_data = {data['mailing_model_id'][0]: data['mailing_model_id_count'] for data in filter_data}
        for mailing in self:
            mailing.mailing_filter_count = mapped_data.get(mailing.mailing_model_id.id, 0)

    @api.depends('mailing_model_id')
    def _compute_mailing_model_real(self):
        for mailing in self:
            mailing.mailing_model_real = 'mailing.contact' if mailing.mailing_model_id.model == 'mailing.list' else mailing.mailing_model_id.model

    @api.depends('mailing_model_id', 'contact_list_ids', 'mailing_type', 'mailing_filter_id')
    def _compute_mailing_domain(self):
        for mailing in self:
            if not mailing.mailing_model_id:
                mailing.mailing_domain = ''
            elif mailing.mailing_filter_id:
                mailing.mailing_domain = mailing.mailing_filter_id.mailing_domain
            else:
                mailing.mailing_domain = repr(mailing._get_default_mailing_domain())

    @api.depends('mailing_model_name')
    def _compute_mailing_filter_id(self):
        for mailing in self:
            mailing.mailing_filter_id = False

    @api.depends('schedule_type')
    def _compute_schedule_date(self):
        for mailing in self:
            if mailing.schedule_type == 'now' or not mailing.schedule_date:
                mailing.schedule_date = False

    @api.depends('state', 'schedule_date', 'sent_date', 'next_departure')
    def _compute_calendar_date(self):
        for mailing in self:
            if mailing.state == 'done':
                mailing.calendar_date = mailing.sent_date
            elif mailing.state == 'in_queue':
                mailing.calendar_date = mailing.next_departure
            elif mailing.state == 'sending':
                mailing.calendar_date = fields.Datetime.now()
            else:
                mailing.calendar_date = False

    @api.depends('body_arch')
    def _compute_is_body_empty(self):
        for mailing in self:
            mailing.is_body_empty = tools.is_html_empty(mailing.body_arch)

    def _compute_mail_server_available(self):
        self.mail_server_available = self.env['ir.config_parameter'].sudo().get_param('mass_mailing.outgoing_mail_server')

    # Overrides of mail.render.mixin
    @api.depends('mailing_model_real')
    def _compute_render_model(self):
        for mailing in self:
            mailing.render_model = mailing.mailing_model_real

    @api.depends('mailing_type')
    def _compute_mailing_type_description(self):
        for mailing in self:
            mailing.mailing_type_description = dict(self._fields.get('mailing_type').selection).get(mailing.mailing_type)

    @api.depends(lambda self: self._get_ab_testing_description_modifying_fields())
    def _compute_ab_testing_description(self):
        mailing_ab_test = self.filtered('ab_testing_enabled')
        (self - mailing_ab_test).ab_testing_description = False
        for mailing in mailing_ab_test:
            mailing.ab_testing_description = self.env['ir.qweb']._render(
                'mass_mailing.ab_testing_description',
                mailing._get_ab_testing_description_values()
            )

    def _get_ab_testing_description_modifying_fields(self):
        return ['ab_testing_enabled', 'ab_testing_pc', 'ab_testing_schedule_datetime', 'ab_testing_winner_selection', 'campaign_id']

    # ------------------------------------------------------
    # ORM
    # ------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        ab_testing_cron = self.env.ref('mass_mailing.ir_cron_mass_mailing_ab_testing').sudo()
        for values in vals_list:
            if values.get('body_html'):
                values['body_html'] = self._convert_inline_images_to_urls(values['body_html'])
            if values.get('ab_testing_schedule_datetime'):
                at = fields.Datetime.from_string(values['ab_testing_schedule_datetime'])
                ab_testing_cron._trigger(at=at)
        mailings = super().create(vals_list)
        mailings._create_ab_testing_utm_campaigns()
        mailings._fix_attachment_ownership()

        return mailings

    def write(self, values):
        if values.get('body_html'):
            values['body_html'] = self._convert_inline_images_to_urls(values['body_html'])
        # If ab_testing is already enabled on a mailing and the campaign is removed, we raise a ValidationError
        if values.get('campaign_id') is False and any(mailing.ab_testing_enabled for mailing in self) and 'ab_testing_enabled' not in values:
            raise ValidationError(_("A campaign should be set when A/B test is enabled"))

        result = super(MassMailing, self).write(values)
        if values.get('ab_testing_enabled'):
            self._create_ab_testing_utm_campaigns()
        self._fix_attachment_ownership()

        if any(self.mapped('ab_testing_schedule_datetime')):
            schedule_date = min(m.ab_testing_schedule_datetime for m in self if m.ab_testing_schedule_datetime)
            ab_testing_cron = self.env.ref('mass_mailing.ir_cron_mass_mailing_ab_testing').sudo()
            ab_testing_cron._trigger(at=schedule_date)

        return result

    def _create_ab_testing_utm_campaigns(self):
        """ Creates the A/B test campaigns for the mailings that do not have campaign set already """
        campaign_vals = [
            mailing._get_default_ab_testing_campaign_values()
            for mailing in self.filtered(lambda mailing: mailing.ab_testing_enabled and not mailing.campaign_id)
        ]
        return self.env['utm.campaign'].create(campaign_vals)

    def _fix_attachment_ownership(self):
        for record in self:
            record.attachment_ids.write({'res_model': record._name, 'res_id': record.id})
        return self

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {}, contact_list_ids=self.contact_list_ids.ids)
        if self.mail_server_id and not self.mail_server_id.active:
            default['mail_server_id'] = self._get_default_mail_server_id()
        return super(MassMailing, self).copy(default=default)

    def _group_expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

    # ------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------

    def action_set_favorite(self):
        """Add the current mailing in the favorites list."""
        self.favorite = True

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _(
                    'Design added to the %s Templates!',
                    ', '.join(self.mapped('mailing_model_id.name')),
                ),
                'next': {'type': 'ir.actions.act_window_close'},
                'sticky': False,
                'type': 'info',
            }
        }

    def action_remove_favorite(self):
        """Remove the current mailing from the favorites list."""
        self.favorite = False

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _(
                    'Design removed from the %s Templates!',
                    ', '.join(self.mapped('mailing_model_id.name')),
                ),
                'next': {'type': 'ir.actions.act_window_close'},
                'sticky': False,
                'type': 'info',
            }
        }

    def action_duplicate(self):
        self.ensure_one()
        mass_mailing_copy = self.copy()
        if mass_mailing_copy:
            context = dict(self.env.context)
            context['form_view_initial_mode'] = 'edit'
            action = {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mailing.mailing',
                'res_id': mass_mailing_copy.id,
                'context': context,
            }
            if self.mailing_type == 'mail':
                action['views'] = [
                    (self.env.ref('mass_mailing.mailing_mailing_view_form_full_width').id, 'form'),
                ]
            return action
        return False

    def action_test(self):
        self.ensure_one()
        ctx = dict(self.env.context, default_mass_mailing_id=self.id, dialog_size='medium')
        return {
            'name': _('Test Mailing'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mailing.mailing.test',
            'target': 'new',
            'context': ctx,
        }

    def action_launch(self):
        self.write({'schedule_type': 'now'})
        return self.action_put_in_queue()

    def action_schedule(self):
        self.ensure_one()
        if self.schedule_date and self.schedule_date > fields.Datetime.now():
            return self.action_put_in_queue()
        action = self.env["ir.actions.actions"]._for_xml_id("mass_mailing.mailing_mailing_schedule_date_action")
        action['context'] = dict(self.env.context, default_mass_mailing_id=self.id, dialog_size='medium')
        return action

    def action_put_in_queue(self):
        self.write({'state': 'in_queue'})
        cron = self.env.ref('mass_mailing.ir_cron_mass_mailing_queue')
        cron._trigger(
            schedule_date or fields.Datetime.now()
            for schedule_date in self.mapped('schedule_date')
        )

    def action_cancel(self):
        self.write({'state': 'draft', 'schedule_date': False, 'schedule_type': 'now', 'next_departure': False})

    def action_retry_failed(self):
        failed_mails = self.env['mail.mail'].sudo().search([
            ('mailing_id', 'in', self.ids),
            ('state', '=', 'exception')
        ])
        failed_mails.mapped('mailing_trace_ids').unlink()
        failed_mails.unlink()
        self.action_put_in_queue()

    def action_view_traces_scheduled(self):
        return self._action_view_traces_filtered('scheduled')

    def action_view_traces_canceled(self):
        return self._action_view_traces_filtered('canceled')

    def action_view_traces_failed(self):
        return self._action_view_traces_filtered('failed')

    def action_view_traces_sent(self):
        return self._action_view_traces_filtered('sent')

    def _action_view_traces_filtered(self, view_filter):
        action = self.env["ir.actions.actions"]._for_xml_id("mass_mailing.mailing_trace_action")
        action['name'] = _('Sent Mailings')
        action['context'] = {'search_default_mass_mailing_id': self.id,}
        filter_key = 'search_default_filter_%s' % (view_filter)
        action['context'][filter_key] = True
        action['views'] = [
            (self.env.ref('mass_mailing.mailing_trace_view_tree_mail').id, 'tree'),
            (self.env.ref('mass_mailing.mailing_trace_view_form').id, 'form')
        ]
        return action

    def action_view_clicked(self):
        model_name = self.env['ir.model']._get('link.tracker').display_name
        recipient = self.env['ir.model']._get(self.mailing_model_real).display_name
        helper_header = _("No %s clicked your mailing yet!", recipient)
        helper_message = _("Link Trackers will measure how many times each link is clicked as well as "
                           "the proportion of %s who clicked at least once in your mailing.", recipient)
        return {
            'name': model_name,
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'link.tracker',
            'domain': [('mass_mailing_id', '=', self.id)],
            'help': Markup('<p class="o_view_nocontent_smiling_face">%s</p><p>%s</p>') % (
                helper_header, helper_message,
            ),
            'context': dict(self._context, create=False)
        }

    def action_view_opened(self):
        return self._action_view_documents_filtered('open')

    def action_view_replied(self):
        return self._action_view_documents_filtered('reply')

    def action_view_bounced(self):
        return self._action_view_documents_filtered('bounce')

    def action_view_delivered(self):
        return self._action_view_documents_filtered('delivered')

    def _action_view_documents_filtered(self, view_filter):
        model_name = self.env['ir.model']._get(self.mailing_model_real).display_name
        helper_header = None
        helper_message = None
        if view_filter == 'reply':
            found_traces = self.mailing_trace_ids.filtered(lambda trace: trace.trace_status == view_filter)
            helper_header = _("No %s replied to your mailing yet!", model_name)
            helper_message = _("To track how many replies this mailing gets, make sure "
                               "its reply-to address belongs to this database.")
        elif view_filter == 'bounce':
            found_traces = self.mailing_trace_ids.filtered(lambda trace: trace.trace_status == view_filter)
            helper_header = _("No %s address bounced yet!", model_name)
            helper_message = _("Bounce happens when a mailing cannot be delivered (fake address, "
                               "server issues, ...). Check each record to see what went wrong.")
        elif view_filter == 'open':
            found_traces = self.mailing_trace_ids.filtered(lambda trace: trace.trace_status in ('open', 'reply'))
            helper_header = _("No %s opened your mailing yet!", model_name)
            helper_message = _("Come back once your mailing has been sent to track who opened your mailing.")
        elif view_filter == 'delivered':
            found_traces = self.mailing_trace_ids.filtered(lambda trace: trace.trace_status in ('sent', 'open', 'reply'))
            helper_header = _("No %s received your mailing yet!", model_name)
            helper_message = _("Wait until your mailing has been sent to check how many recipients you managed to reach.")
        elif view_filter == 'sent':
            found_traces = self.mailing_trace_ids.filtered(lambda trace: trace.sent_datetime)
        else:
            found_traces = self.env['mailing.trace']
        res_ids = found_traces.mapped('res_id')
        action = {
            'name': model_name,
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': self.mailing_model_real,
            'domain': [('id', 'in', res_ids)],
            'context': dict(self._context, create=False),
        }
        if helper_header and helper_message:
            action['help'] = Markup('<p class="o_view_nocontent_smiling_face">%s</p><p>%s</p>') % (
                helper_header, helper_message,
            ),
        return action

    def action_view_mailing_contacts(self):
        """Show the mailing contacts who are in a mailing list selected for this mailing."""
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('mass_mailing.action_view_mass_mailing_contacts')
        if self.contact_list_ids:
            action['context'] = {
                'default_mailing_list_ids': self.contact_list_ids[0].ids,
                'default_subscription_list_ids': [(0, 0, {'list_id': self.contact_list_ids[0].id})],
            }
        action['domain'] = [('list_ids', 'in', self.contact_list_ids.ids)]
        return action

    @api.model
    def action_fetch_favorites(self, extra_domain=None):
        """Return all mailings set as favorite and skip mailings with empty body.

        Return archived mailing templates as well, so the user can archive the templates
        while keeping using it, without cluttering the Kanban view if they're a lot of
        templates.
        """
        domain = [('favorite', '=', True)]
        if extra_domain:
            domain = expression.AND([domain, extra_domain])

        values_list = self.with_context(active_test=False).search_read(
            domain=domain,
            fields=['id', 'subject', 'body_arch', 'user_id', 'mailing_model_id'],
            order='favorite_date DESC',
        )

        values_list = [
            values for values in values_list
            if not tools.is_html_empty(values['body_arch'])
        ]

        # You see first the mailings without responsible, then your mailings and then the others
        values_list.sort(
            key=lambda values:
            values['user_id'][0] != self.env.user.id if values['user_id'] else -1
        )

        return values_list

    def update_opt_out(self, email, list_ids, value):
        if len(list_ids) > 0:
            model = self.env['mailing.contact'].with_context(active_test=False)
            records = model.search([('email_normalized', '=', tools.email_normalize(email))])
            opt_out_records = self.env['mailing.contact.subscription'].search([
                ('contact_id', 'in', records.ids),
                ('list_id', 'in', list_ids),
                ('opt_out', '!=', value)
            ])

            opt_out_records.write({'opt_out': value})
            message = _('The recipient <strong>unsubscribed from %s</strong> mailing list(s)') \
                if value else _('The recipient <strong>subscribed to %s</strong> mailing list(s)')
            for record in records:
                # filter the list_id by record
                record_lists = opt_out_records.filtered(lambda rec: rec.contact_id.id == record.id)
                if len(record_lists) > 0:
                    record.sudo().message_post(body=message % ', '.join(str(list.name) for list in record_lists.mapped('list_id')))

    # ------------------------------------------------------
    # A/B Test
    # ------------------------------------------------------

    def action_compare_versions(self):
        self.ensure_one()
        if not self.campaign_id:
            raise ValueError(_("No mailing campaign has been found"))
        action = {
            'name': _('A/B Tests'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,kanban,form,calendar,graph',
            'res_model': 'mailing.mailing',
            'domain': [('campaign_id', '=', self.campaign_id.id), ('ab_testing_enabled', '=', True), ('mailing_type', '=', self.mailing_type)],
        }
        if self.mailing_type == 'mail':
            action['views'] = [
                (False, 'tree'),
                (False, 'kanban'),
                (self.env.ref('mass_mailing.mailing_mailing_view_form_full_width').id, 'form'),
                (False, 'calendar'),
                (False, 'graph'),
            ]
        return action

    def action_send_winner_mailing(self):
        """Send the winner mailing based on the winner selection field.
        This action is used in 2 cases:
            - When the user clicks on a button to send the winner mailing. There is only one mailing in self
            - When the cron is executed to send winner mailing based on the A/B testing schedule datetime. In this
            case 'self' contains all the mailing for the campaigns so we just need to take the first to determine the
            winner.
        If the winner mailing is computed automatically, we sudo the mailings of the campaign in order to sort correctly
        the mailings based on the selection that can be used with sub-modules like CRM and Sales
        """
        if len(self.campaign_id) != 1:
            raise ValueError(_("To send the winner mailing the same campaign should be used by the mailings"))
        if any(mailing.ab_testing_completed for mailing in self):
            raise ValueError(_("To send the winner mailing the campaign should not have been completed."))
        final_mailing = self[0]
        sorted_by = final_mailing._get_ab_testing_winner_selection()['value']
        if sorted_by != 'manual':
            ab_testing_mailings = final_mailing._get_ab_testing_siblings_mailings().sudo()
            selected_mailings = ab_testing_mailings.filtered(lambda m: m.state == 'done').sorted(sorted_by, reverse=True)
            if selected_mailings:
                final_mailing = selected_mailings[0]
            else:
                raise ValidationError(_("No mailing for this A/B testing campaign has been sent yet! Send one first and try again later."))
        return final_mailing.action_select_as_winner()

    def action_select_as_winner(self):
        self.ensure_one()
        if not self.ab_testing_enabled:
            raise ValueError(_("A/B test option has not been enabled"))
        self.campaign_id.write({
            'ab_testing_completed': True,
        })
        final_mailing = self.copy({
            'ab_testing_pc': 100,
        })
        final_mailing.action_launch()
        action = self.env['ir.actions.act_window']._for_xml_id('mass_mailing.action_ab_testing_open_winner_mailing')
        action['res_id'] = final_mailing.id
        if self.mailing_type == 'mail':
            action['views'] = [
                (self.env.ref('mass_mailing.mailing_mailing_view_form_full_width').id, 'form'),
            ]
        return action

    def _get_ab_testing_description_values(self):
        self.ensure_one()

        other_ab_testing_mailings = self._get_ab_testing_siblings_mailings().filtered(lambda m: m.id != self.id)
        other_ab_testing_pc = sum([mailing.ab_testing_pc for mailing in other_ab_testing_mailings])
        return {
            'mailing': self,
            'ab_testing_winner_selection_description': self._get_ab_testing_winner_selection()['description'],
            'other_ab_testing_pc': other_ab_testing_pc,
            'remaining_ab_testing_pc': 100 - (other_ab_testing_pc + self.ab_testing_pc),
        }

    def _get_ab_testing_siblings_mailings(self):
        return self.campaign_id.mailing_mail_ids.filtered(lambda m: m.ab_testing_enabled)

    def _get_ab_testing_winner_selection(self):
        ab_testing_winner_selection_description = dict(
            self._fields.get('ab_testing_winner_selection').related_field.selection
        ).get(self.ab_testing_winner_selection)
        return {
            'value': self.ab_testing_winner_selection,
            'description': ab_testing_winner_selection_description,
        }

    def _get_default_ab_testing_campaign_values(self, values=None):
        values = values or dict()
        return {
            'ab_testing_schedule_datetime': values.get('ab_testing_schedule_datetime') or self.ab_testing_schedule_datetime,
            'ab_testing_winner_selection': values.get('ab_testing_winner_selection') or self.ab_testing_winner_selection,
            'mailing_mail_ids': self.ids,
            'name': _('A/B Test: %s', values.get('subject') or self.subject or fields.Datetime.now()),
            'user_id': values.get('user_id') or self.user_id.id or self.env.user.id,
        }

    # ------------------------------------------------------
    # Email Sending
    # ------------------------------------------------------

    def _get_opt_out_list(self):
        """ Give list of opt-outed emails, depending on specific model-based
        computation if available.

        :return list: opt-outed emails, preferably normalized (aka not records)
        """
        self.ensure_one()
        opt_out = {}
        target = self.env[self.mailing_model_real]
        if hasattr(self.env[self.mailing_model_name], '_mailing_get_opt_out_list'):
            opt_out = self.env[self.mailing_model_name]._mailing_get_opt_out_list(self)
            _logger.info(
                "Mass-mailing %s targets %s, blacklist: %s emails",
                self, target._name, len(opt_out))
        else:
            _logger.info("Mass-mailing %s targets %s, no opt out list available", self, target._name)
        return opt_out

    def _get_link_tracker_values(self):
        self.ensure_one()
        vals = {'mass_mailing_id': self.id}

        if self.campaign_id:
            vals['campaign_id'] = self.campaign_id.id
        if self.source_id:
            vals['source_id'] = self.source_id.id
        if self.medium_id:
            vals['medium_id'] = self.medium_id.id
        return vals

    def _get_seen_list(self):
        """Returns a set of emails already targeted by current mailing/campaign (no duplicates)"""
        self.ensure_one()
        target = self.env[self.mailing_model_real]

        # avoid loading a large number of records in memory
        # + use a basic heuristic for extracting emails
        query = """
            SELECT lower(substring(t.%(mail_field)s, '([^ ,;<@]+@[^> ,;]+)'))
              FROM mailing_trace s
              JOIN %(target)s t ON (s.res_id = t.id)
              %(join_domain)s
             WHERE substring(t.%(mail_field)s, '([^ ,;<@]+@[^> ,;]+)') IS NOT NULL
              %(where_domain)s
        """

        # Apply same 'get email field' rule from mail_thread.message_get_default_recipients
        if 'partner_id' in target._fields and target._fields['partner_id'].store:
            mail_field = 'email'
            query = """
                SELECT lower(substring(p.%(mail_field)s, '([^ ,;<@]+@[^> ,;]+)'))
                  FROM mailing_trace s
                  JOIN %(target)s t ON (s.res_id = t.id)
                  JOIN res_partner p ON (t.partner_id = p.id)
                  %(join_domain)s
                 WHERE substring(p.%(mail_field)s, '([^ ,;<@]+@[^> ,;]+)') IS NOT NULL
                  %(where_domain)s
            """
        elif issubclass(type(target), self.pool['mail.thread.blacklist']):
            mail_field = 'email_normalized'
        elif 'email_from' in target._fields and target._fields['email_from'].store:
            mail_field = 'email_from'
        elif 'partner_email' in target._fields and target._fields['partner_email'].store:
            mail_field = 'partner_email'
        elif 'email' in target._fields and target._fields['email'].store:
            mail_field = 'email'
        else:
            raise UserError(_("Unsupported mass mailing model %s", self.mailing_model_id.name))

        if self.ab_testing_enabled:
            query += """
               AND s.campaign_id = %%(mailing_campaign_id)s;
            """
        else:
            query += """
               AND s.mass_mailing_id = %%(mailing_id)s
               AND s.model = %%(target_model)s;
            """
        join_domain, where_domain = self._get_seen_list_extra()
        query = query % {'target': target._table, 'mail_field': mail_field, 'join_domain': join_domain, 'where_domain': where_domain}
        params = {'mailing_id': self.id, 'mailing_campaign_id': self.campaign_id.id, 'target_model': self.mailing_model_real}
        self._cr.execute(query, params)
        seen_list = set(m[0] for m in self._cr.fetchall())
        _logger.info(
            "Mass-mailing %s has already reached %s %s emails", self, len(seen_list), target._name)
        return seen_list

    def _get_seen_list_extra(self):
        return ('', '')

    def _get_mass_mailing_context(self):
        """Returns extra context items with pre-filled blacklist and seen list for massmailing"""
        return {
            'post_convert_links': self._get_link_tracker_values(),
        }

    def _get_recipients(self):
        mailing_domain = self._parse_mailing_domain()
        res_ids = self.env[self.mailing_model_real].search(mailing_domain).ids

        # randomly choose a fragment
        if self.ab_testing_enabled and self.ab_testing_pc < 100:
            contact_nbr = self.env[self.mailing_model_real].search_count(mailing_domain)
            topick = 0
            if contact_nbr:
                topick = max(int(contact_nbr / 100.0 * self.ab_testing_pc), 1)
            if self.campaign_id and self.ab_testing_enabled:
                already_mailed = self.campaign_id._get_mailing_recipients()[self.campaign_id.id]
            else:
                already_mailed = set([])
            remaining = set(res_ids).difference(already_mailed)
            if topick > len(remaining) or (len(remaining) > 0 and topick == 0):
                topick = len(remaining)
            res_ids = random.sample(sorted(remaining), topick)
        return res_ids

    def _get_remaining_recipients(self):
        res_ids = self._get_recipients()
        trace_domain = [('model', '=', self.mailing_model_real)]
        if self.ab_testing_enabled and self.ab_testing_pc == 100:
            trace_domain = expression.AND([trace_domain, [('mass_mailing_id', 'in', self._get_ab_testing_siblings_mailings().ids)]])
        else:
            trace_domain = expression.AND([trace_domain, [
                ('res_id', 'in', res_ids),
                ('mass_mailing_id', '=', self.id),
            ]])
        already_mailed = self.env['mailing.trace'].search_read(trace_domain, ['res_id'])
        done_res_ids = {record['res_id'] for record in already_mailed}
        return [rid for rid in res_ids if rid not in done_res_ids]

    def _get_unsubscribe_url(self, email_to, res_id):
        url = werkzeug.urls.url_join(
            self.get_base_url(), 'mail/mailing/%(mailing_id)s/unsubscribe?%(params)s' % {
                'mailing_id': self.id,
                'params': werkzeug.urls.url_encode({
                    'res_id': res_id,
                    'email': email_to,
                    'token': self._unsubscribe_token(res_id, email_to),
                }),
            }
        )
        return url

    def _get_view_url(self, email_to, res_id):
        url = werkzeug.urls.url_join(
            self.get_base_url(), 'mailing/%(mailing_id)s/view?%(params)s' % {
                'mailing_id': self.id,
                'params': werkzeug.urls.url_encode({
                    'res_id': res_id,
                    'email': email_to,
                    'token': self._unsubscribe_token(res_id, email_to),
                }),
            }
        )
        return url

    def action_send_mail(self, res_ids=None):
        author_id = self.env.user.partner_id.id

        # If no recipient is passed, we don't want to use the recipients of the first
        # mailing for all the others
        initial_res_ids = res_ids
        for mailing in self:
            if not initial_res_ids:
                res_ids = mailing._get_remaining_recipients()
            if not res_ids:
                raise UserError(_('There are no recipients selected.'))

            composer_values = {
                'author_id': author_id,
                'attachment_ids': [(4, attachment.id) for attachment in mailing.attachment_ids],
                'body': mailing._prepend_preview(mailing.body_html, mailing.preview),
                'subject': mailing.subject,
                'model': mailing.mailing_model_real,
                'email_from': mailing.email_from,
                'record_name': False,
                'composition_mode': 'mass_mail',
                'mass_mailing_id': mailing.id,
                'mailing_list_ids': [(4, l.id) for l in mailing.contact_list_ids],
                'reply_to_force_new': mailing.reply_to_mode == 'new',
                'template_id': None,
                'mail_server_id': mailing.mail_server_id.id,
            }
            if mailing.reply_to_mode == 'new':
                composer_values['reply_to'] = mailing.reply_to

            composer = self.env['mail.compose.message'].with_context(active_ids=res_ids).create(composer_values)
            extra_context = mailing._get_mass_mailing_context()
            composer = composer.with_context(active_ids=res_ids, **extra_context)
            # auto-commit except in testing mode
            auto_commit = not getattr(threading.current_thread(), 'testing', False)
            composer._action_send_mail(auto_commit=auto_commit)
            mailing.write({
                'state': 'done',
                'sent_date': fields.Datetime.now(),
                # send the KPI mail only if it's the first sending
                'kpi_mail_required': not mailing.sent_date,
            })
        return True

    def convert_links(self):
        res = {}
        for mass_mailing in self:
            html = mass_mailing.body_html if mass_mailing.body_html else ''

            vals = {'mass_mailing_id': mass_mailing.id}

            if mass_mailing.campaign_id:
                vals['campaign_id'] = mass_mailing.campaign_id.id
            if mass_mailing.source_id:
                vals['source_id'] = mass_mailing.source_id.id
            if mass_mailing.medium_id:
                vals['medium_id'] = mass_mailing.medium_id.id

            res[mass_mailing.id] = mass_mailing._shorten_links(html, vals, blacklist=['/unsubscribe_from_list', '/view'])

        return res

    @api.model
    def _process_mass_mailing_queue(self):
        mass_mailings = self.search([('state', 'in', ('in_queue', 'sending')), '|', ('schedule_date', '<', fields.Datetime.now()), ('schedule_date', '=', False)])
        for mass_mailing in mass_mailings:
            user = mass_mailing.write_uid or self.env.user
            mass_mailing = mass_mailing.with_context(**user.with_user(user).context_get())
            if len(mass_mailing._get_remaining_recipients()) > 0:
                mass_mailing.state = 'sending'
                mass_mailing.action_send_mail()
            else:
                mass_mailing.write({
                    'state': 'done',
                    'sent_date': fields.Datetime.now(),
                    # send the KPI mail only if it's the first sending
                    'kpi_mail_required': not mass_mailing.sent_date,
                })

        if self.env['ir.config_parameter'].sudo().get_param('mass_mailing.mass_mailing_reports'):
            mailings = self.env['mailing.mailing'].search([
                ('kpi_mail_required', '=', True),
                ('state', '=', 'done'),
                ('sent_date', '<=', fields.Datetime.now() - relativedelta(days=1)),
                ('sent_date', '>=', fields.Datetime.now() - relativedelta(days=5)),
            ])
            if mailings:
                mailings._action_send_statistics()

    # ------------------------------------------------------
    # STATISTICS
    # ------------------------------------------------------

    def _action_send_statistics(self):
        """Send an email to the responsible of each finished mailing with the statistics."""
        self.kpi_mail_required = False

        mails_sudo = self.env['mail.mail'].sudo()
        for mailing in self:
            if mailing.user_id:
                mailing = mailing.with_user(mailing.user_id).with_context(
                    lang=mailing.user_id.lang or self._context.get('lang')
                )
            mailing_type = mailing._get_pretty_mailing_type()
            mail_user = mailing.user_id or self.env.user
            mail_company = mail_user.company_id

            link_trackers = self.env['link.tracker'].search(
                [('mass_mailing_id', '=', mailing.id)]
            ).sorted('count', reverse=True)
            link_trackers_body = self.env['ir.qweb']._render(
                'mass_mailing.mass_mailing_kpi_link_trackers',
                {
                    'object': mailing,
                    'link_trackers': link_trackers,
                    'mailing_type': mailing_type,
                },
            )
            rendering_data = {
                'body': tools.html_sanitize(link_trackers_body),
                'company': mail_company,
                'user': mail_user,
                'display_mobile_banner': True,
                ** mailing._prepare_statistics_email_values(),
            }
            if mail_user.has_group('mass_mailing.group_mass_mailing_user'):
                rendering_data['mailing_report_token'] = self._get_unsubscribe_token(mail_user.id)
                rendering_data['user_id'] = mail_user.id

            rendered_body = self.env['ir.qweb']._render(
                'digest.digest_mail_main',
                rendering_data
            )

            full_mail = self.env['mail.render.mixin']._render_encapsulate(
                'digest.digest_mail_layout',
                rendered_body,
            )

            mail_values = {
                'auto_delete': True,
                'author_id': mail_user.partner_id.id,
                'email_from': mail_user.email_formatted,
                'email_to': mail_user.email_formatted,
                'body_html': full_mail,
                'reply_to': mail_company.email_formatted or mail_user.email_formatted,
                'state': 'outgoing',
                'subject': _('24H Stats of %(mailing_type)s "%(mailing_name)s"',
                             mailing_type=mailing._get_pretty_mailing_type(),
                             mailing_name=mailing.subject
                            ),
            }
            mails_sudo += self.env['mail.mail'].sudo().create(mail_values)
        return mails_sudo

    def _prepare_statistics_email_values(self):
        """Return some statistics that will be displayed in the mailing statistics email.

        Each item in the returned list will be displayed as a table, with a title and
        1, 2 or 3 columns.
        """
        self.ensure_one()
        mailing_type = self._get_pretty_mailing_type()
        kpi = {}
        if self.mailing_type == 'mail':
            kpi = {
                'kpi_fullname': _('Engagement on %(expected)i %(mailing_type)s Sent',
                                  expected=self.expected,
                                  mailing_type=mailing_type
                                 ),
                'kpi_col1': {
                    'value': f'{self.received_ratio}%',
                    'col_subtitle': _('RECEIVED (%i)', self.delivered),
                },
                'kpi_col2': {
                    'value': f'{self.opened_ratio}%',
                    'col_subtitle': _('OPENED (%i)', self.opened),
                },
                'kpi_col3': {
                    'value': f'{self.replied_ratio}%',
                    'col_subtitle': _('REPLIED (%i)', self.replied),
                },
                'kpi_action': None,
                'kpi_name': self.mailing_type,
            }

        random_tip = self.env['digest.tip'].search(
            [('group_id.category_id', '=', self.env.ref('base.module_category_marketing_email_marketing').id)]
        )
        if random_tip:
            random_tip = random.choice(random_tip).tip_description

        formatted_date = tools.format_datetime(
            self.env, self.sent_date, self.user_id.tz, 'MMM dd, YYYY', self.user_id.lang
        ) if self.sent_date else False

        web_base_url = self.get_base_url()

        return {
            'title': _('24H Stats of %(mailing_type)s "%(mailing_name)s"',
                       mailing_type=mailing_type,
                       mailing_name=self.subject
                       ),
            'top_button_label': _('More Info'),
            'top_button_url': url_join(web_base_url, f'/web#id={self.id}&model=mailing.mailing&view_type=form'),
            'kpi_data': [
                kpi,
                {
                    'kpi_fullname': _('Business Benefits on %(expected)i %(mailing_type)s Sent',
                                      expected=self.expected,
                                      mailing_type=mailing_type
                                     ),
                    'kpi_action': None,
                    'kpi_col1': {},
                    'kpi_col2': {},
                    'kpi_col3': {},
                    'kpi_name': 'trace',
                },
            ],
            'tips': [random_tip] if random_tip else False,
            'formatted_date': formatted_date,
        }

    def _get_pretty_mailing_type(self):
        return _('Emails')

    def _get_unsubscribe_token(self, user_id):
        """Generate a secure hash for this user. It allows to opt out from
        mailing reports while keeping some security in that process. """
        return tools.hmac(self.env(su=True), 'mailing-report-deactivated', user_id)

    # ------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------

    def _get_default_mailing_domain(self):
        mailing_domain = []
        if hasattr(self.env[self.mailing_model_name], '_mailing_get_default_domain'):
            mailing_domain = self.env[self.mailing_model_name]._mailing_get_default_domain(self)

        if self.mailing_type == 'mail' and 'is_blacklisted' in self.env[self.mailing_model_name]._fields:
            mailing_domain = expression.AND([[('is_blacklisted', '=', False)], mailing_domain])

        return mailing_domain

    def _parse_mailing_domain(self):
        self.ensure_one()
        try:
            mailing_domain = literal_eval(self.mailing_domain)
        except Exception:
            mailing_domain = [('id', 'in', [])]
        return mailing_domain

    def _unsubscribe_token(self, res_id, email):
        """Generate a secure hash for this mailing list and parameters.

        This is appended to the unsubscription URL and then checked at
        unsubscription time to ensure no malicious unsubscriptions are
        performed.

        :param int res_id:
            ID of the resource that will be unsubscribed.

        :param str email:
            Email of the resource that will be unsubscribed.
        """
        secret = self.env["ir.config_parameter"].sudo().get_param("database.secret")
        token = (self.env.cr.dbname, self.id, int(res_id), tools.ustr(email))
        return hmac.new(secret.encode('utf-8'), repr(token).encode('utf-8'), hashlib.sha512).hexdigest()

    def _convert_inline_images_to_urls(self, body_html):
        """
        Find inline base64 encoded images, make an attachement out of
        them and replace the inline image with an url to the attachement.
        """

        def _image_to_url(b64image: bytes):
            """Store an image in an attachement and returns an url"""
            attachment = self.env['ir.attachment'].create({
                'datas': b64image,
                'name': "cropped_image_mailing_{}".format(self.id),
                'type': 'binary',})

            attachment.generate_access_token()

            return '/web/image/%s?access_token=%s' % (
                attachment.id, attachment.access_token)

        modified = False
        root = lxml.html.fromstring(body_html)
        for node in root.iter('img'):
            match = image_re.match(node.attrib.get('src', ''))
            if match:
                mime = match.group(1)  # unsed
                image = match.group(2).encode()  # base64 image as bytes

                node.attrib['src'] = _image_to_url(image)
                modified = True

        if modified:
            return lxml.html.tostring(root, encoding='unicode')

        return body_html
