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
from datetime import datetime
from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_join

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.osv import expression

_logger = logging.getLogger(__name__)

MASS_MAILING_BUSINESS_MODELS = [
    'crm.lead',
    'event.registration',
    'hr.applicant',
    'res.partner',
    'event.track',
    'sale.order',
    'mailing.list',
    'mailing.contact'
]

# Syntax of the data URL Scheme: https://tools.ietf.org/html/rfc2397#section-3
# Used to find inline images
image_re = re.compile(r"data:(image/[A-Za-z]+);base64,(.*)")


class MassMailing(models.Model):
    """ MassMailing models a wave of emails for a mass mailign campaign.
    A mass mailing is an occurence of sending emails. """
    _name = 'mailing.mailing'
    _description = 'Mass Mailing'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'mail.render.mixin']
    _order = 'sent_date DESC'
    _inherits = {'utm.source': 'source_id'}
    _rec_name = "subject"

    @api.model
    def default_get(self, fields):
        vals = super(MassMailing, self).default_get(fields)
        if 'contact_list_ids' in fields and not vals.get('contact_list_ids') and vals.get('mailing_model_id'):
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
    subject = fields.Char('Subject', help='Subject of your Mailing', required=True, translate=True)
    preview = fields.Char(
        'Preview', translate=True,
        help='Catchy preview sentence that encourages recipients to open this email.\n'
             'In most inboxes, this is displayed next to the subject.\n'
             'Keep it empty if you prefer the first characters of your email content to appear instead.')
    email_from = fields.Char(string='Send From', required=True,
        default=lambda self: self.env.user.email_formatted)
    sent_date = fields.Datetime(string='Sent Date', copy=False)
    schedule_date = fields.Datetime(string='Scheduled for', tracking=True)
    # don't translate 'body_arch', the translations are only on 'body_html'
    body_arch = fields.Html(string='Body', translate=False)
    body_html = fields.Html(string='Body converted to be sent by mail', sanitize_attributes=False)
    attachment_ids = fields.Many2many('ir.attachment', 'mass_mailing_ir_attachments_rel',
        'mass_mailing_id', 'attachment_id', string='Attachments')
    keep_archives = fields.Boolean(string='Keep Archives')
    campaign_id = fields.Many2one('utm.campaign', string='UTM Campaign', index=True)
    source_id = fields.Many2one('utm.source', string='Source', required=True, ondelete='cascade',
                                help="This is the link source, e.g. Search Engine, another domain, or name of email list")
    medium_id = fields.Many2one(
        'utm.medium', string='Medium',
        compute='_compute_medium_id', readonly=False, store=True,
        help="UTM Medium: delivery method (email, sms, ...)")
    state = fields.Selection([('draft', 'Draft'), ('in_queue', 'In Queue'), ('sending', 'Sending'), ('done', 'Sent')],
        string='Status', required=True, tracking=True, copy=False, default='draft', group_expand='_group_expand_states')
    color = fields.Integer(string='Color Index')
    user_id = fields.Many2one('res.users', string='Responsible', tracking=True,  default=lambda self: self.env.user)
    # mailing options
    mailing_type = fields.Selection([('mail', 'Email')], string="Mailing Type", default="mail", required=True)
    reply_to_mode = fields.Selection([
        ('thread', 'Recipient Followers'), ('email', 'Specified Email Address')],
        string='Reply-To Mode', compute='_compute_reply_to_mode',
        readonly=False, store=True,
        help='Thread: replies go to target document. Email: replies are routed to a given email.')
    reply_to = fields.Char(
        string='Reply To', compute='_compute_reply_to', readonly=False, store=True,
        help='Preferred Reply-To Address')
    # recipients
    mailing_model_real = fields.Char(string='Recipients Real Model', compute='_compute_model')
    mailing_model_id = fields.Many2one(
        'ir.model', string='Recipients Model', ondelete='cascade', required=True,
        domain=[('model', 'in', MASS_MAILING_BUSINESS_MODELS)],
        default=lambda self: self.env.ref('mass_mailing.model_mailing_list').id)
    mailing_model_name = fields.Char(
        string='Recipients Model Name', related='mailing_model_id.model',
        readonly=True, related_sudo=True)
    mailing_domain = fields.Char(
        string='Domain', compute='_compute_mailing_domain',
        readonly=False, store=True)
    mail_server_id = fields.Many2one('ir.mail_server', string='Mail Server',
        default=_get_default_mail_server_id,
        help="Use a specific mail server in priority. Otherwise Odoo relies on the first outgoing mail server available (based on their sequencing) as it does for normal mails.")
    contact_list_ids = fields.Many2many('mailing.list', 'mail_mass_mailing_list_rel', string='Mailing Lists')
    contact_ab_pc = fields.Integer(string='A/B Testing percentage',
        help='Percentage of the contacts that will be mailed. Recipients will be taken randomly.', default=100)
    unique_ab_testing = fields.Boolean(string='Allow A/B Testing', default=False,
        help='If checked, recipients will be mailed only once for the whole campaign. '
             'This lets you send different mailings to randomly selected recipients and test '
             'the effectiveness of the mailings, without causing duplicate messages.')
    kpi_mail_required = fields.Boolean('KPI mail required', copy=False)
    # statistics data
    mailing_trace_ids = fields.One2many('mailing.trace', 'mass_mailing_id', string='Emails Statistics')
    total = fields.Integer(compute="_compute_total")
    scheduled = fields.Integer(compute="_compute_statistics")
    expected = fields.Integer(compute="_compute_statistics")
    ignored = fields.Integer(compute="_compute_statistics")
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

    def _compute_total(self):
        for mass_mailing in self:
            total = self.env[mass_mailing.mailing_model_real].search_count(mass_mailing._parse_mailing_domain())
            if mass_mailing.contact_ab_pc < 100:
                total = int(total / 100.0 * mass_mailing.contact_ab_pc)
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
            'scheduled', 'expected', 'ignored', 'sent', 'delivered', 'opened',
            'clicked', 'replied', 'bounced', 'failed', 'received_ratio',
            'opened_ratio', 'replied_ratio', 'bounced_ratio',
        ):
            self[key] = False
        if not self.ids:
            return
        # ensure traces are sent to db
        self.flush()
        self.env.cr.execute("""
            SELECT
                m.id as mailing_id,
                COUNT(s.id) AS expected,
                COUNT(CASE WHEN s.sent is not null THEN 1 ELSE null END) AS sent,
                COUNT(CASE WHEN s.scheduled is not null AND s.sent is null AND s.exception is null AND s.ignored is null AND s.bounced is null THEN 1 ELSE null END) AS scheduled,
                COUNT(CASE WHEN s.scheduled is not null AND s.sent is null AND s.exception is null AND s.ignored is not null THEN 1 ELSE null END) AS ignored,
                COUNT(CASE WHEN s.sent is not null AND s.exception is null AND s.bounced is null THEN 1 ELSE null END) AS delivered,
                COUNT(CASE WHEN s.opened is not null THEN 1 ELSE null END) AS opened,
                COUNT(CASE WHEN s.clicked is not null THEN 1 ELSE null END) AS clicked,
                COUNT(CASE WHEN s.replied is not null THEN 1 ELSE null END) AS replied,
                COUNT(CASE WHEN s.bounced is not null THEN 1 ELSE null END) AS bounced,
                COUNT(CASE WHEN s.exception is not null THEN 1 ELSE null END) AS failed
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
            total = (row['expected'] - row['ignored']) or 1
            row['received_ratio'] = 100.0 * row['delivered'] / total
            row['opened_ratio'] = 100.0 * row['opened'] / total
            row['replied_ratio'] = 100.0 * row['replied'] / total
            row['bounced_ratio'] = 100.0 * row['bounced'] / total
            self.browse(row.pop('mailing_id')).update(row)

    def _compute_next_departure(self):
        cron_next_call = self.env.ref('mass_mailing.ir_cron_mass_mailing_queue').sudo().nextcall
        str2dt = fields.Datetime.from_string
        cron_time = str2dt(cron_next_call)
        for mass_mailing in self:
            if mass_mailing.schedule_date:
                schedule_date = str2dt(mass_mailing.schedule_date)
                mass_mailing.next_departure = max(schedule_date, cron_time)
            else:
                mass_mailing.next_departure = cron_time

    @api.depends('mailing_type')
    def _compute_medium_id(self):
        for mailing in self:
            if mailing.mailing_type == 'mail' and not mailing.medium_id:
                mailing.medium_id = self.env.ref('utm.utm_medium_email').id

    @api.depends('mailing_model_id')
    def _compute_model(self):
        for record in self:
            record.mailing_model_real = (record.mailing_model_name != 'mailing.list') and record.mailing_model_name or 'mailing.contact'

    @api.depends('mailing_model_real')
    def _compute_reply_to_mode(self):
        for mailing in self:
            if mailing.mailing_model_real in ['res.partner', 'mailing.contact']:
                mailing.reply_to_mode = 'email'
            else:
                mailing.reply_to_mode = 'thread'

    @api.depends('reply_to_mode')
    def _compute_reply_to(self):
        for mailing in self:
            if mailing.reply_to_mode == 'email' and not mailing.reply_to:
                mailing.reply_to = self.env.user.email_formatted
            elif mailing.reply_to_mode == 'thread':
                mailing.reply_to = False

    @api.depends('mailing_model_name', 'contact_list_ids')
    def _compute_mailing_domain(self):
        for mailing in self:
            if not mailing.mailing_model_name:
                mailing.mailing_domain = ''
            else:
                mailing.mailing_domain = repr(mailing._get_default_mailing_domain())

    # ------------------------------------------------------
    # ORM
    # ------------------------------------------------------

    @api.model
    def create(self, values):
        if values.get('subject') and not values.get('name'):
            values['name'] = "%s %s" % (values['subject'], datetime.strftime(fields.datetime.now(), tools.DEFAULT_SERVER_DATETIME_FORMAT))
        if values.get('body_html'):
            values['body_html'] = self._convert_inline_images_to_urls(values['body_html'])
        return super(MassMailing, self).create(values)

    def write(self, values):
        if values.get('body_html'):
            values['body_html'] = self._convert_inline_images_to_urls(values['body_html'])
        return super(MassMailing, self).write(values)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {},
                       name=_('%s (copy)', self.name),
                       contact_list_ids=self.contact_list_ids.ids)
        return super(MassMailing, self).copy(default=default)

    def _group_expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

    # ------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------

    def action_duplicate(self):
        self.ensure_one()
        mass_mailing_copy = self.copy()
        if mass_mailing_copy:
            context = dict(self.env.context)
            context['form_view_initial_mode'] = 'edit'
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mailing.mailing',
                'res_id': mass_mailing_copy.id,
                'context': context,
            }
        return False

    def action_test(self):
        self.ensure_one()
        ctx = dict(self.env.context, default_mass_mailing_id=self.id)
        return {
            'name': _('Test Mailing'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mailing.mailing.test',
            'target': 'new',
            'context': ctx,
        }

    def action_schedule(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("mass_mailing.mailing_mailing_schedule_date_action")
        action['context'] = dict(self.env.context, default_mass_mailing_id=self.id)
        return action

    def action_put_in_queue(self):
        self.write({'state': 'in_queue'})

    def action_cancel(self):
        self.write({'state': 'draft', 'schedule_date': False, 'next_departure': False})

    def action_retry_failed(self):
        failed_mails = self.env['mail.mail'].sudo().search([
            ('mailing_id', 'in', self.ids),
            ('state', '=', 'exception')
        ])
        failed_mails.mapped('mailing_trace_ids').unlink()
        failed_mails.unlink()
        self.write({'state': 'in_queue'})

    def action_view_traces_scheduled(self):
        return self._action_view_traces_filtered('scheduled')

    def action_view_traces_ignored(self):
        return self._action_view_traces_filtered('ignored')

    def action_view_traces_failed(self):
        return self._action_view_traces_filtered('failed')

    def action_view_traces_sent(self):
        return self._action_view_traces_filtered('sent')

    def _action_view_traces_filtered(self, view_filter):
        action = self.env["ir.actions.actions"]._for_xml_id("mass_mailing.mailing_trace_action")
        action['name'] = _('%s Traces') % (self.name)
        action['context'] = {'search_default_mass_mailing_id': self.id,}
        filter_key = 'search_default_filter_%s' % (view_filter)
        action['context'][filter_key] = True
        return action

    def action_view_clicked(self):
        model_name = self.env['ir.model']._get('link.tracker').display_name
        return {
            'name': model_name,
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'link.tracker',
            'domain': [('mass_mailing_id.id', '=', self.id)],
            'context': dict(self._context, create=False)
        }

    def action_view_opened(self):
        return self._action_view_documents_filtered('opened')

    def action_view_replied(self):
        return self._action_view_documents_filtered('replied')

    def action_view_bounced(self):
        return self._action_view_documents_filtered('bounced')

    def action_view_delivered(self):
        return self._action_view_documents_filtered('delivered')

    def _action_view_documents_filtered(self, view_filter):
        if view_filter in ('opened', 'replied', 'bounced'):
            opened_stats = self.mailing_trace_ids.filtered(lambda stat: stat[view_filter])
        elif view_filter == ('delivered'):
            opened_stats = self.mailing_trace_ids.filtered(lambda stat: stat.sent and not stat.bounced)
        else:
            opened_stats = self.env['mailing.trace']
        res_ids = opened_stats.mapped('res_id')
        model_name = self.env['ir.model']._get(self.mailing_model_real).display_name
        return {
            'name': model_name,
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': self.mailing_model_real,
            'domain': [('id', 'in', res_ids)],
            'context': dict(self._context, create=False)
        }

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
    # Email Sending
    # ------------------------------------------------------

    def _get_opt_out_list(self):
        """Returns a set of emails opted-out in target model"""
        self.ensure_one()
        opt_out = {}
        target = self.env[self.mailing_model_real]
        if self.mailing_model_real == "mailing.contact":
            # if user is opt_out on One list but not on another
            # or if two user with same email address, one opted in and the other one opted out, send the mail anyway
            # TODO DBE Fixme : Optimise the following to get real opt_out and opt_in
            target_list_contacts = self.env['mailing.contact.subscription'].search(
                [('list_id', 'in', self.contact_list_ids.ids)])
            opt_out_contacts = target_list_contacts.filtered(lambda rel: rel.opt_out).mapped('contact_id.email_normalized')
            opt_in_contacts = target_list_contacts.filtered(lambda rel: not rel.opt_out).mapped('contact_id.email_normalized')
            opt_out = set(c for c in opt_out_contacts if c not in opt_in_contacts)

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
             WHERE substring(t.%(mail_field)s, '([^ ,;<@]+@[^> ,;]+)') IS NOT NULL
        """

        # Apply same 'get email field' rule from mail_thread.message_get_default_recipients
        if 'partner_id' in target._fields:
            mail_field = 'email'
            query = """
                SELECT lower(substring(p.%(mail_field)s, '([^ ,;<@]+@[^> ,;]+)'))
                  FROM mailing_trace s
                  JOIN %(target)s t ON (s.res_id = t.id)
                  JOIN res_partner p ON (t.partner_id = p.id)
                 WHERE substring(p.%(mail_field)s, '([^ ,;<@]+@[^> ,;]+)') IS NOT NULL
            """
        elif issubclass(type(target), self.pool['mail.thread.blacklist']):
            mail_field = 'email_normalized'
        elif 'email_from' in target._fields:
            mail_field = 'email_from'
        elif 'partner_email' in target._fields:
            mail_field = 'partner_email'
        elif 'email' in target._fields:
            mail_field = 'email'
        else:
            raise UserError(_("Unsupported mass mailing model %s", self.mailing_model_id.name))

        if self.unique_ab_testing:
            query +="""
               AND s.campaign_id = %%(mailing_campaign_id)s;
            """
        else:
            query +="""
               AND s.mass_mailing_id = %%(mailing_id)s
               AND s.model = %%(target_model)s;
            """
        query = query % {'target': target._table, 'mail_field': mail_field}
        params = {'mailing_id': self.id, 'mailing_campaign_id': self.campaign_id.id, 'target_model': self.mailing_model_real}
        self._cr.execute(query, params)
        seen_list = set(m[0] for m in self._cr.fetchall())
        _logger.info(
            "Mass-mailing %s has already reached %s %s emails", self, len(seen_list), target._name)
        return seen_list

    def _get_mass_mailing_context(self):
        """Returns extra context items with pre-filled blacklist and seen list for massmailing"""
        return {
            'mass_mailing_opt_out_list': self._get_opt_out_list(),
            'mass_mailing_seen_list': self._get_seen_list(),
            'post_convert_links': self._get_link_tracker_values(),
        }

    def _get_recipients(self):
        mailing_domain = self._parse_mailing_domain()
        res_ids = self.env[self.mailing_model_real].search(mailing_domain).ids

        # randomly choose a fragment
        if self.contact_ab_pc < 100:
            contact_nbr = self.env[self.mailing_model_real].search_count(mailing_domain)
            topick = int(contact_nbr / 100.0 * self.contact_ab_pc)
            if self.campaign_id and self.unique_ab_testing:
                already_mailed = self.campaign_id._get_mailing_recipients()[self.campaign_id.id]
            else:
                already_mailed = set([])
            remaining = set(res_ids).difference(already_mailed)
            if topick > len(remaining):
                topick = len(remaining)
            res_ids = random.sample(remaining, topick)
        return res_ids

    def _get_remaining_recipients(self):
        res_ids = self._get_recipients()
        already_mailed = self.env['mailing.trace'].search_read([
            ('model', '=', self.mailing_model_real),
            ('res_id', 'in', res_ids),
            ('mass_mailing_id', '=', self.id)], ['res_id'])
        done_res_ids = {record['res_id'] for record in already_mailed}
        return [rid for rid in res_ids if rid not in done_res_ids]

    def _get_unsubscribe_url(self, email_to, res_id):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = werkzeug.urls.url_join(
            base_url, 'mail/mailing/%(mailing_id)s/unsubscribe?%(params)s' % {
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
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = werkzeug.urls.url_join(
            base_url, 'mailing/%(mailing_id)s/view?%(params)s' % {
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
                'no_auto_thread': mailing.reply_to_mode != 'thread',
                'template_id': None,
                'mail_server_id': mailing.mail_server_id.id,
            }
            if mailing.reply_to_mode == 'email':
                composer_values['reply_to'] = mailing.reply_to

            composer = self.env['mail.compose.message'].with_context(active_ids=res_ids).create(composer_values)
            extra_context = mailing._get_mass_mailing_context()
            composer = composer.with_context(active_ids=res_ids, **extra_context)
            # auto-commit except in testing mode
            auto_commit = not getattr(threading.currentThread(), 'testing', False)
            composer.send_mail(auto_commit=auto_commit)
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

        for mailing in self:
            user = mailing.user_id
            mailing = mailing.with_context(lang=user.lang or self._context.get('lang'))

            link_trackers = self.env['link.tracker'].search(
                [('mass_mailing_id', '=', mailing.id)]
            ).sorted('count', reverse=True)
            link_trackers_body = self.env['ir.qweb']._render(
                'mass_mailing.mass_mailing_kpi_link_trackers',
                {'object': mailing, 'link_trackers': link_trackers},
            )

            rendered_body = self.env['ir.qweb']._render(
                'digest.digest_mail_main',
                {
                    'body': tools.html_sanitize(link_trackers_body),
                    'company': user.company_id,
                    'user': user,
                    'display_mobile_banner': True,
                    ** mailing._prepare_statistics_email_values()
                },
            )

            full_mail = self.env['mail.render.mixin']._render_encapsulate(
                'digest.digest_mail_layout',
                rendered_body,
            )

            mail_values = {
                'subject': _('24H Stats of mailing "%s"') % mailing.subject,
                'email_from': user.email_formatted,
                'email_to': user.email_formatted,
                'body_html': full_mail,
                'auto_delete': True,
            }
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send(raise_exception=False)

    def _prepare_statistics_email_values(self):
        """Return some statistics that will be displayed in the mailing statistics email.

        Each item in the returned list will be displayed as a table, with a title and
        1, 2 or 3 columns.
        """
        self.ensure_one()

        random_tip = self.env['digest.tip'].search(
            [('group_id.category_id', '=', self.env.ref('base.module_category_marketing_email_marketing').id)]
        )
        if random_tip:
            random_tip = random.choice(random_tip).tip_description

        formatted_date = tools.format_datetime(
            self.env, self.sent_date, self.user_id.tz, 'MMM dd, YYYY',  self.user_id.lang
        ) if self.sent_date else False

        web_base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        return {
            'title': _('24H Stats of mailing'),
            'sub_title': '"%s"' % self.subject,
            'top_button_label': _('More Info'),
            'top_button_url': url_join(web_base_url, f'/web#id={self.id}&model=mailing.mailing&view_type=form'),
            'kpi_data': [
                {
                    'kpi_fullname': _('Engagement on %i Emails Sent') % self.sent,
                    'kpi_action': None,
                    'kpi_col1': {
                        'value': f'{self.received_ratio}%',
                        'col_subtitle': '%s (%i)' % (_('RECEIVED'), self.delivered),
                    },
                    'kpi_col2': {
                        'value': f'{self.opened_ratio}%',
                        'col_subtitle': '%s (%i)' % (_('OPENED'), self.opened),
                    },
                    'kpi_col3': {
                        'value': f'{self.replied_ratio}%',
                        'col_subtitle': '%s (%i)' % (_('REPLIED'), self.replied),
                    },
                }, {
                    'kpi_fullname': _('Business Benefits on %i Emails Sent') % self.sent,
                    'kpi_action': None,
                    'kpi_col1': {},
                    'kpi_col2': {},
                    'kpi_col3': {},
                },
            ],
            'tips': [random_tip] if random_tip else False,
            'formatted_date': formatted_date,
        }

    # ------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------

    def _get_default_mailing_domain(self):
        mailing_domain = []
        if self.mailing_model_name == 'mailing.list' and self.contact_list_ids:
            mailing_domain = [('list_ids', 'in', self.contact_list_ids.ids)]

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
            return lxml.html.tostring(root)

        return body_html
