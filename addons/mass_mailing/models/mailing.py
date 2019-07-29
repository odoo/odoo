# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import logging
import lxml
import random
import re
import threading
from ast import literal_eval
from base64 import b64encode

from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

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


class MailingTag(models.Model):
    """Model of categories of mass mailing, i.e. marketing, newsletter, ... """
    _name = 'mailing.tag'
    _description = 'Mass Mailing Tag'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class MailingStage(models.Model):

    """Stage for mass mailing campaigns. """
    _name = 'mailing.stage'
    _description = 'Mass Mailing Campaign Stage'
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer()


class MassMailingCampaign(models.Model):
    """Model of mass mailing campaigns. """
    _name = "mail.mass_mailing.campaign"
    _description = 'Mass Mailing Campaign'
    _rec_name = "campaign_id"
    _inherits = {'utm.campaign': 'campaign_id'}

    stage_id = fields.Many2one('mailing.stage', string='Stage', ondelete='restrict', required=True, 
        default=lambda self: self.env['mailing.stage'].search([], limit=1),
        group_expand='_group_expand_stage_ids')
    user_id = fields.Many2one(
        'res.users', string='Responsible',
        required=True, default=lambda self: self.env.uid)
    campaign_id = fields.Many2one('utm.campaign', 'campaign_id',
        required=True, ondelete='cascade',  help="This name helps you tracking your different campaign efforts, e.g. Fall_Drive, Christmas_Special")
    source_id = fields.Many2one('utm.source', string='Source',
            help="This is the link source, e.g. Search Engine, another domain,or name of email list", default=lambda self: self.env.ref('utm.utm_source_newsletter', False))
    medium_id = fields.Many2one('utm.medium', string='Medium',
            help="This is the delivery method, e.g. Postcard, Email, or Banner Ad", default=lambda self: self.env.ref('utm.utm_medium_email', False))
    tag_ids = fields.Many2many(
        'mailing.tag', 'mail_mass_mailing_tag_rel',
        'tag_id', 'campaign_id', string='Tags')
    mass_mailing_ids = fields.One2many(
        'mailing.mailing', 'mass_mailing_campaign_id',
        string='Mass Mailings')
    unique_ab_testing = fields.Boolean(string='Allow A/B Testing', default=False,
        help='If checked, recipients will be mailed only once for the whole campaign. '
             'This lets you send different mailings to randomly selected recipients and test '
             'the effectiveness of the mailings, without causing duplicate messages.')
    color = fields.Integer(string='Color Index')
    clicks_ratio = fields.Integer(compute="_compute_clicks_ratio", string="Number of clicks")
    # trace statistics fields
    total = fields.Integer(compute="_compute_statistics")
    scheduled = fields.Integer(compute="_compute_statistics")
    failed = fields.Integer(compute="_compute_statistics")
    ignored = fields.Integer(compute="_compute_statistics")
    sent = fields.Integer(compute="_compute_statistics", string="Sent Emails")
    delivered = fields.Integer(compute="_compute_statistics")
    opened = fields.Integer(compute="_compute_statistics")
    replied = fields.Integer(compute="_compute_statistics")
    bounced = fields.Integer(compute="_compute_statistics")
    received_ratio = fields.Integer(compute="_compute_statistics", string='Received Ratio')
    opened_ratio = fields.Integer(compute="_compute_statistics", string='Opened Ratio')
    replied_ratio = fields.Integer(compute="_compute_statistics", string='Replied Ratio')
    bounced_ratio = fields.Integer(compute="_compute_statistics", string='Bounced Ratio')
    total_mailings = fields.Integer(compute="_compute_total_mailings", string='Mailings')

    def _compute_clicks_ratio(self):
        self.env.cr.execute("""
            SELECT COUNT(DISTINCT(stats.id)) AS nb_mails, COUNT(DISTINCT(clicks.mailing_trace_id)) AS nb_clicks, stats.mass_mailing_campaign_id AS id
            FROM mailing_trace AS stats
            LEFT OUTER JOIN link_tracker_click AS clicks ON clicks.mailing_trace_id = stats.id
            WHERE stats.mass_mailing_campaign_id IN %s
            GROUP BY stats.mass_mailing_campaign_id
        """, (tuple(self.ids), ))

        campaign_data = self.env.cr.dictfetchall()
        mapped_data = dict([(c['id'], 100 * c['nb_clicks'] / c['nb_mails']) for c in campaign_data])
        for campaign in self:
            campaign.clicks_ratio = mapped_data.get(campaign.id, 0)

    def _compute_statistics(self):
        """ Compute statistics of the mass mailing campaign """
        self.env['mail_mail_statistics'].flush(self.env['mail_mail_statistics']._fields)
        self.env.cr.execute("""
            SELECT
                c.id as campaign_id,
                COUNT(s.id) AS total,
                COUNT(CASE WHEN s.sent is not null THEN 1 ELSE null END) AS sent,
                COUNT(CASE WHEN s.scheduled is not null AND s.sent is null AND s.exception is null AND s.ignored is null THEN 1 ELSE null END) AS scheduled,
                COUNT(CASE WHEN s.scheduled is not null AND s.sent is null AND s.exception is not null THEN 1 ELSE null END) AS failed,
                COUNT(CASE WHEN s.scheduled is not null AND s.sent is null AND s.exception is null AND s.ignored is not null THEN 1 ELSE null END) AS ignored,
                COUNT(CASE WHEN s.id is not null AND s.bounced is null THEN 1 ELSE null END) AS delivered,
                COUNT(CASE WHEN s.opened is not null THEN 1 ELSE null END) AS opened,
                COUNT(CASE WHEN s.replied is not null THEN 1 ELSE null END) AS replied ,
                COUNT(CASE WHEN s.bounced is not null THEN 1 ELSE null END) AS bounced
            FROM
                mailing_trace s
            RIGHT JOIN
                mail_mass_mailing_campaign c
                ON (c.id = s.mass_mailing_campaign_id)
            WHERE
                c.id IN %s
            GROUP BY
                c.id
        """, (tuple(self.ids), ))

        for row in self.env.cr.dictfetchall():
            total = (row['total'] - row['ignored']) or 1
            row['delivered'] = row['sent'] - row['bounced']
            row['received_ratio'] = 100.0 * row['delivered'] / total
            row['opened_ratio'] = 100.0 * row['opened'] / total
            row['replied_ratio'] = 100.0 * row['replied'] / total
            row['bounced_ratio'] = 100.0 * row['bounced'] / total
            self.browse(row.pop('campaign_id')).update(row)

    def _compute_total_mailings(self):
        campaign_data = self.env['mailing.mailing'].read_group(
            [('mass_mailing_campaign_id', 'in', self.ids)],
            ['mass_mailing_campaign_id'], ['mass_mailing_campaign_id'])
        mapped_data = dict([(c['mass_mailing_campaign_id'][0], c['mass_mailing_campaign_id_count']) for c in campaign_data])
        for campaign in self:
            campaign.total_mailings = mapped_data.get(campaign.id, 0)

    def _get_recipients(self, model=None):
        """Return the recipients of a mailing campaign. This is based on the statistics
        build for each mailing. """
        res = dict.fromkeys(self.ids, {})
        for campaign in self:
            domain = [('mass_mailing_campaign_id', '=', campaign.id)]
            if model:
                domain += [('model', '=', model)]
            res[campaign.id] = set(self.env['mailing.trace'].search(domain).mapped('res_id'))
        return res

    @api.model
    def _group_expand_stage_ids(self, stages, domain, order):
        """ Read group customization in order to display all the stages in the
            kanban view, even if they are empty
        """
        stage_ids = stages._search([], order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)


class MassMailing(models.Model):
    """ MassMailing models a wave of emails for a mass mailign campaign.
    A mass mailing is an occurence of sending emails. """
    _name = 'mailing.mailing'
    _description = 'Mass Mailing'
    # number of periods for tracking mail_mail statistics
    _period_number = 6
    _order = 'sent_date DESC'
    _inherits = {'utm.source': 'source_id'}
    _rec_name = "source_id"

    @api.model
    def _get_default_mail_server_id(self):
        server_id = self.env['ir.config_parameter'].sudo().get_param('mass_mailing.mail_server_id')
        try:
            server_id = literal_eval(server_id) if server_id else False
            return self.env['ir.mail_server'].search([('id', '=', server_id)]).id
        except ValueError:
            return False

    @api.model
    def default_get(self, fields):
        res = super(MassMailing, self).default_get(fields)
        if 'reply_to_mode' in fields and not 'reply_to_mode' in res and res.get('mailing_model_real'):
            if res['mailing_model_real'] in ['res.partner', 'mailing.contact']:
                res['reply_to_mode'] = 'email'
            else:
                res['reply_to_mode'] = 'thread'
        return res

    active = fields.Boolean(default=True)
    subject = fields.Char('Subject', help='Subject of emails to send', required=True, translate=True)
    email_from = fields.Char(string='From', required=True,
        default=lambda self: self.env['mail.message']._get_default_from())
    sent_date = fields.Datetime(string='Sent Date', oldname='date', copy=False)
    schedule_date = fields.Datetime(string='Schedule in the Future')
    # don't translate 'body_arch', the translations are only on 'body_html'
    body_arch = fields.Html(string='Body', translate=False)
    body_html = fields.Html(string='Body converted to be send by mail', sanitize_attributes=False)
    attachment_ids = fields.Many2many('ir.attachment', 'mass_mailing_ir_attachments_rel',
        'mass_mailing_id', 'attachment_id', string='Attachments')
    keep_archives = fields.Boolean(string='Keep Archives')
    mass_mailing_campaign_id = fields.Many2one('mail.mass_mailing.campaign', string='Mass Mailing Campaign')
    campaign_id = fields.Many2one('utm.campaign', string='Campaign',
                                  help="This name helps you tracking your different campaign efforts, e.g. Fall_Drive, Christmas_Special")
    source_id = fields.Many2one('utm.source', string='Source', required=True, ondelete='cascade',
                                help="This is the link source, e.g. Search Engine, another domain, or name of email list")
    medium_id = fields.Many2one('utm.medium', string='Medium', help="Delivery method: Email")
    clicks_ratio = fields.Integer(compute="_compute_clicks_ratio", string="Number of Clicks")
    state = fields.Selection([('draft', 'Draft'), ('in_queue', 'In Queue'), ('sending', 'Sending'), ('done', 'Sent')],
        string='Status', required=True, copy=False, default='draft', group_expand='_group_expand_states')
    color = fields.Integer(string='Color Index')
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    # mailing options
    reply_to_mode = fields.Selection(
        [('thread', 'Recipient Followers'), ('email', 'Specified Email Address')], string='Reply-To Mode', required=True)
    reply_to = fields.Char(string='Reply To', help='Preferred Reply-To Address',
        default=lambda self: self.env['mail.message']._get_default_from())
    # recipients
    mailing_model_real = fields.Char(compute='_compute_model', string='Recipients Real Model', default='mailing.contact', required=True)
    mailing_model_id = fields.Many2one('ir.model', string='Recipients Model', domain=[('model', 'in', MASS_MAILING_BUSINESS_MODELS)],
        default=lambda self: self.env.ref('mass_mailing.model_mailing_list').id)
    mailing_model_name = fields.Char(related='mailing_model_id.model', string='Recipients Model Name', readonly=True, related_sudo=True)
    mailing_domain = fields.Char(string='Domain', oldname='domain', default=[])
    mail_server_id = fields.Many2one('ir.mail_server', string='Mail Server',
        default=_get_default_mail_server_id,
        help="Use a specific mail server in priority. Otherwise Odoo relies on the first outgoing mail server available (based on their sequencing) as it does for normal mails.")
    contact_list_ids = fields.Many2many('mailing.list', 'mail_mass_mailing_list_rel',
        string='Mailing Lists')
    contact_ab_pc = fields.Integer(string='A/B Testing percentage',
        help='Percentage of the contacts that will be mailed. Recipients will be taken randomly.', default=100)
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
    bounced_ratio = fields.Integer(compute="_compute_statistics", String='Bounced Ratio')
    next_departure = fields.Datetime(compute="_compute_next_departure", string='Scheduled date')

    def _compute_total(self):
        for mass_mailing in self:
            mass_mailing.total = len(mass_mailing.sudo()._get_recipients())

    def _compute_clicks_ratio(self):
        self.env.cr.execute("""
            SELECT COUNT(DISTINCT(stats.id)) AS nb_mails, COUNT(DISTINCT(clicks.mailing_trace_id)) AS nb_clicks, stats.mass_mailing_id AS id
            FROM mailing_trace AS stats
            LEFT OUTER JOIN link_tracker_click AS clicks ON clicks.mailing_trace_id = stats.id
            WHERE stats.mass_mailing_id IN %s
            GROUP BY stats.mass_mailing_id
        """, (tuple(self.ids), ))

        mass_mailing_data = self.env.cr.dictfetchall()
        mapped_data = dict([(m['id'], 100 * m['nb_clicks'] / m['nb_mails']) for m in mass_mailing_data])
        for mass_mailing in self:
            mass_mailing.clicks_ratio = mapped_data.get(mass_mailing.id, 0)

    @api.depends('mailing_model_id')
    def _compute_model(self):
        for record in self:
            record.mailing_model_real = (record.mailing_model_name != 'mailing.list') and record.mailing_model_name or 'mailing.contact'

    def _compute_statistics(self):
        """ Compute statistics of the mass mailing """
        self.env.cr.execute("""
            SELECT
                m.id as mailing_id,
                COUNT(s.id) AS expected,
                COUNT(CASE WHEN s.sent is not null THEN 1 ELSE null END) AS sent,
                COUNT(CASE WHEN s.scheduled is not null AND s.sent is null AND s.exception is null AND s.ignored is null THEN 1 ELSE null END) AS scheduled,
                COUNT(CASE WHEN s.scheduled is not null AND s.sent is null AND s.exception is not null THEN 1 ELSE null END) AS failed,
                COUNT(CASE WHEN s.scheduled is not null AND s.sent is null AND s.exception is null AND s.ignored is not null THEN 1 ELSE null END) AS ignored,
                COUNT(CASE WHEN s.sent is not null AND s.bounced is null THEN 1 ELSE null END) AS delivered,
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
            total = row['expected'] = (row['expected'] - row['ignored']) or 1
            row['received_ratio'] = 100.0 * row['delivered'] / total
            row['opened_ratio'] = 100.0 * row['opened'] / total
            row['clicks_ratio'] = 100.0 * row['clicked'] / total
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

    @api.onchange('mass_mailing_campaign_id')
    def _onchange_mass_mailing_campaign_id(self):
        if self.mass_mailing_campaign_id:
            self.campaign_id = self.mass_mailing_campaign_id.campaign_id.id

    @api.onchange('mailing_model_id', 'contact_list_ids')
    def _onchange_model_and_list(self):
        mailing_domain = []
        if self.mailing_model_name:
            if self.mailing_model_name == 'mailing.list':
                if self.contact_list_ids:
                    mailing_domain.append(('list_ids', 'in', self.contact_list_ids.ids))
                else:
                    mailing_domain.append((0, '=', 1))
            elif self.mailing_model_name == 'res.partner':
                mailing_domain.append(('customer', '=', True))
            elif 'opt_out' in self.env[self.mailing_model_name]._fields and not self.mailing_domain:
                mailing_domain.append(('opt_out', '=', False))
        else:
            mailing_domain.append((0, '=', 1))
        self.mailing_domain = repr(mailing_domain)

    @api.onchange('subject')
    def _onchange_subject(self):
        if self.subject and not self.name:
            self.name = self.subject

    # ------------------------------------------------------
    # ORM
    # ------------------------------------------------------

    @api.model
    def create(self, values):
        if values.get('name') and not values.get('subject'):
            values['subject'] = values['name']
        if values.get('body_html'):
            values['body_html'] = self._convert_inline_images_to_urls(values['body_html'])
        if 'medium_id' not in values:
            values['medium_id'] = self.env.ref('utm.utm_medium_email').id
        return super(MassMailing, self).create(values)

    def write(self, values):
        if values.get('body_html'):
            values['body_html'] = self._convert_inline_images_to_urls(values['body_html'])
        return super(MassMailing, self).write(values)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {},
                       name=_('%s (copy)') % self.name)
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

    def action_test_mailing(self):
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

    def action_schedule_date(self):
        self.ensure_one()
        action = self.env.ref('mass_mailing.mailing_mailing_schedule_date_action').read()[0]
        action['context'] = dict(self.env.context, default_mass_mailing_id=self.id)
        return action

    def put_in_queue(self):
        self.write({'state': 'in_queue'})

    def cancel_mass_mailing(self):
        self.write({'state': 'draft', 'schedule_date': False})

    def retry_failed_mail(self):
        failed_mails = self.env['mail.mail'].search([('mailing_id', 'in', self.ids), ('state', '=', 'exception')])
        failed_mails.mapped('mailing_trace_ids').unlink()
        failed_mails.sudo().unlink()
        res_ids = self._get_recipients()
        except_mailed = self.env['mailing.trace'].search([
            ('model', '=', self.mailing_model_real),
            ('res_id', 'in', res_ids),
            ('exception', '!=', False),
            ('mass_mailing_id', '=', self.id)]).unlink()
        self.write({'state': 'in_queue'})

    def action_view_sent(self):
        return self._action_view_documents_filtered('sent')

    def action_view_opened(self):
        return self._action_view_documents_filtered('opened')

    def action_view_replied(self):
        return self._action_view_documents_filtered('replied')

    def action_view_bounced(self):
        return self._action_view_documents_filtered('bounced')

    def action_view_clicked(self):
        return self._action_view_documents_filtered('clicked')

    def action_view_delivered(self):
        return self._action_view_documents_filtered('delivered')

    def _action_view_documents_filtered(self, view_filter):
        if view_filter in ('sent', 'opened', 'replied', 'bounced', 'clicked'):
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
                    record.sudo().message_post(body=_(message % ', '.join(str(list.name) for list in record_lists.mapped('list_id'))))

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

    def _get_convert_links(self):
        vals = {
            'mass_mailing_id': self.id,
            'source_id': self.source_id.id,
            'medium_id': self.medium_id.id,
        }
        if self.mass_mailing_campaign_id:
            vals['mass_mailing_campaign_id'] = self.mass_mailing_campaign_id.id
            vals['campaign_id'] = self.mass_mailing_campaign_id.campaign_id.id
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
        elif issubclass(type(target), self.pool['mail.address.mixin']):
            mail_field = 'email_normalized'
        elif 'email_from' in target._fields:
            mail_field = 'email_from'
        elif 'partner_email' in target._fields:
            mail_field = 'partner_email'
        elif 'email' in target._fields:
            mail_field = 'email'
        else:
            raise UserError(_("Unsupported mass mailing model %s") % self.mailing_model_id.name)

        if self.mass_mailing_campaign_id.unique_ab_testing:
            query +="""
               AND s.mass_mailing_campaign_id = %%(mailing_campaign_id)s;
            """
        else:
            query +="""
               AND s.mass_mailing_id = %%(mailing_id)s
               AND s.model = %%(target_model)s;
            """
        query = query % {'target': target._table, 'mail_field': mail_field}
        params = {'mailing_id': self.id, 'mailing_campaign_id': self.mass_mailing_campaign_id.id, 'target_model': self.mailing_model_real}
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
            'post_convert_links': self._get_convert_links(),
        }

    def _get_recipients(self):
        if self.mailing_domain:
            domain = safe_eval(self.mailing_domain)
            res_ids = self.env[self.mailing_model_real].search(domain).ids
        else:
            res_ids = []
            domain = [('id', 'in', res_ids)]

        # randomly choose a fragment
        if self.contact_ab_pc < 100:
            contact_nbr = self.env[self.mailing_model_real].search_count(domain)
            topick = int(contact_nbr / 100.0 * self.contact_ab_pc)
            if self.mass_mailing_campaign_id and self.mass_mailing_campaign_id.unique_ab_testing:
                already_mailed = self.mass_mailing_campaign_id._get_recipients()[self.mass_mailing_campaign_id.id]
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
        done_res_ids = [record['res_id'] for record in already_mailed]
        return [rid for rid in res_ids if rid not in done_res_ids]

    def action_send_mail(self, res_ids=None):
        author_id = self.env.user.partner_id.id

        for mailing in self:
            if not res_ids:
                res_ids = mailing._get_remaining_recipients()
            if not res_ids:
                raise UserError(_('There is no recipients selected.'))

            composer_values = {
                'author_id': author_id,
                'attachment_ids': [(4, attachment.id) for attachment in mailing.attachment_ids],
                'body': mailing.body_html,
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
            extra_context = self._get_mass_mailing_context()
            composer = composer.with_context(active_ids=res_ids, **extra_context)
            # auto-commit except in testing mode
            auto_commit = not getattr(threading.currentThread(), 'testing', False)
            composer.send_mail(auto_commit=auto_commit)
            mailing.write({'state': 'done', 'sent_date': fields.Datetime.now()})
        return True

    def convert_links(self):
        res = {}
        for mass_mailing in self:
            utm_mixin = mass_mailing.mass_mailing_campaign_id if mass_mailing.mass_mailing_campaign_id else mass_mailing
            html = mass_mailing.body_html if mass_mailing.body_html else ''

            vals = {'mass_mailing_id': mass_mailing.id}

            if mass_mailing.mass_mailing_campaign_id:
                vals['mass_mailing_campaign_id'] = mass_mailing.mass_mailing_campaign_id.id
            if utm_mixin.campaign_id:
                vals['campaign_id'] = utm_mixin.campaign_id.id
            if utm_mixin.source_id:
                vals['source_id'] = utm_mixin.source_id.id
            if utm_mixin.medium_id:
                vals['medium_id'] = utm_mixin.medium_id.id

            res[mass_mailing.id] = self.env['link.tracker'].convert_links(html, vals, blacklist=['/unsubscribe_from_list'])

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
                mass_mailing.write({'state': 'done', 'sent_date': fields.Datetime.now()})

    # ------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------

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
