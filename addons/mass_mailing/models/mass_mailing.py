# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
from datetime import datetime
import logging
import random

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from odoo.tools.translate import html_translate

_logger = logging.getLogger(__name__)

class MassMailingTag(models.Model):
    """Model of categories of mass mailing, i.e. marketing, newsletter, ... """
    _name = 'mail.mass_mailing.tag'
    _description = 'Mass Mailing Tag'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
            ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class MassMailingList(models.Model):
    """Model of a contact list. """
    _name = 'mail.mass_mailing.list'
    _order = 'name'
    _description = 'Mailing List'

    name = fields.Char(string='Mailing List', required=True)
    active = fields.Boolean(default=True)
    create_date = fields.Datetime(string='Creation Date')
    contact_nbr = fields.Integer(compute="_compute_contact_nbr", string='Number of Contacts')

    # Compute number of contacts non opt-out for a mailing list
    def _compute_contact_nbr(self):
        self.env.cr.execute('''
            select
                list_id, count(*)
            from
                mail_mass_mailing_contact_list_rel r 
                left join mail_mass_mailing_contact c on (r.contact_id=c.id)
            where
                c.opt_out <> true
            group by
                list_id
        ''')
        data = dict(self.env.cr.fetchall())
        for mailing_list in self:
            mailing_list.contact_nbr = data.get(mailing_list.id, 0)

class MassMailingContact(models.Model):
    """Model of a contact. This model is different from the partner model
    because it holds only some basic information: name, email. The purpose is to
    be able to deal with large contact list to email without bloating the partner
    base."""
    _name = 'mail.mass_mailing.contact'
    _inherit = 'mail.thread'
    _description = 'Mass Mailing Contact'
    _order = 'email'
    _rec_name = 'email'

    name = fields.Char()
    company_name = fields.Char(string='Company Name')
    title_id = fields.Many2one('res.partner.title', string='Title')
    email = fields.Char(required=True)
    create_date = fields.Datetime(string='Creation Date')
    list_ids = fields.Many2many(
        'mail.mass_mailing.list', 'mail_mass_mailing_contact_list_rel',
        'contact_id', 'list_id', string='Mailing Lists')
    opt_out = fields.Boolean(string='Opt Out', help='The contact has chosen not to receive mails anymore from this list')
    unsubscription_date = fields.Datetime(string='Unsubscription Date')
    message_bounce = fields.Integer(string='Bounced', help='Counter of the number of bounced emails for this contact.')
    country_id = fields.Many2one('res.country', string='Country')
    tag_ids = fields.Many2many('res.partner.category', string='Tags')

    @api.model
    def create(self, vals):
        if 'opt_out' in vals:
            vals['unsubscription_date'] = vals['opt_out'] and fields.Datetime.now()
        return super(MassMailingContact, self).create(vals)

    @api.multi
    def write(self, vals):
        if 'opt_out' in vals:
            vals['unsubscription_date'] = vals['opt_out'] and fields.Datetime.now()
        return super(MassMailingContact, self).write(vals)

    def get_name_email(self, name):
        name, email = self.env['res.partner']._parse_partner_name(name)
        if name and not email:
            email = name
        if email and not name:
            name = email
        return name, email

    @api.model
    def name_create(self, name):
        name, email = self.get_name_email(name)
        contact = self.create({'name': name, 'email': email})
        return contact.name_get()[0]

    @api.model
    def add_to_list(self, name, list_id):
        name, email = self.get_name_email(name)
        contact = self.create({'name': name, 'email': email, 'list_ids': [(4, list_id)]})
        return contact.name_get()[0]

    @api.multi
    def message_get_default_recipients(self):
        return dict((record.id, {'partner_ids': [], 'email_to': record.email, 'email_cc': False}) for record in self)


class MassMailingStage(models.Model):

    """Stage for mass mailing campaigns. """
    _name = 'mail.mass_mailing.stage'
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

    stage_id = fields.Many2one('mail.mass_mailing.stage', string='Stage', required=True, 
        default=lambda self: self.env['mail.mass_mailing.stage'].search([], limit=1))
    user_id = fields.Many2one(
        'res.users', string='Responsible',
        required=True, default=lambda self: self.env.uid)
    campaign_id = fields.Many2one('utm.campaign', 'campaign_id',
        required=True, ondelete='cascade',  help="This name helps you tracking your different campaign efforts, e.g. Fall_Drive, Christmas_Special")
    source_id = fields.Many2one('utm.source', string='Source',
            help="This is the link source, e.g. Search Engine, another domain,or name of email list", default=lambda self: self.env.ref('utm.utm_source_newsletter'))
    medium_id = fields.Many2one('utm.medium', string='Medium',
            help="This is the delivery method, e.g. Postcard, Email, or Banner Ad", default=lambda self: self.env.ref('utm.utm_medium_email'))
    tag_ids = fields.Many2many(
        'mail.mass_mailing.tag', 'mail_mass_mailing_tag_rel',
        'tag_id', 'campaign_id', string='Tags')
    mass_mailing_ids = fields.One2many(
        'mail.mass_mailing', 'mass_mailing_campaign_id',
        string='Mass Mailings')
    unique_ab_testing = fields.Boolean(string='Allow A/B Testing', default=True,
        help='If checked, recipients will be mailed only once for the whole campaign. '
             'This lets you send different mailings to randomly selected recipients and test '
             'the effectiveness of the mailings, without causing duplicate messages.')
    color = fields.Integer(string='Color Index')
    clicks_ratio = fields.Integer(compute="_compute_clicks_ratio", string="Number of clicks")
    # stat fields
    total = fields.Integer(compute="_compute_statistics")
    scheduled = fields.Integer(compute="_compute_statistics")
    failed = fields.Integer(compute="_compute_statistics")
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
            SELECT COUNT(DISTINCT(stats.id)) AS nb_mails, COUNT(DISTINCT(clicks.mail_stat_id)) AS nb_clicks, stats.mass_mailing_campaign_id AS id
            FROM mail_mail_statistics AS stats
            LEFT OUTER JOIN link_tracker_click AS clicks ON clicks.mail_stat_id = stats.id
            WHERE stats.mass_mailing_campaign_id IN %s
            GROUP BY stats.mass_mailing_campaign_id
        """, (tuple(self.ids), ))

        campaign_data = self.env.cr.dictfetchall()
        mapped_data = dict([(c['id'], 100 * c['nb_clicks'] / c['nb_mails']) for c in campaign_data])
        for campaign in self:
            campaign.clicks_ratio = mapped_data.get(campaign.id, 0)

    def _compute_statistics(self):
        """ Compute statistics of the mass mailing campaign """
        self.env.cr.execute("""
            SELECT
                c.id as campaign_id,
                COUNT(s.id) AS total,
                COUNT(CASE WHEN s.sent is not null THEN 1 ELSE null END) AS sent,
                COUNT(CASE WHEN s.scheduled is not null AND s.sent is null AND s.exception is null THEN 1 ELSE null END) AS scheduled,
                COUNT(CASE WHEN s.scheduled is not null AND s.sent is null AND s.exception is not null THEN 1 ELSE null END) AS failed,
                COUNT(CASE WHEN s.id is not null AND s.bounced is null THEN 1 ELSE null END) AS delivered,
                COUNT(CASE WHEN s.opened is not null THEN 1 ELSE null END) AS opened,
                COUNT(CASE WHEN s.replied is not null THEN 1 ELSE null END) AS replied ,
                COUNT(CASE WHEN s.bounced is not null THEN 1 ELSE null END) AS bounced
            FROM
                mail_mail_statistics s
            RIGHT JOIN
                mail_mass_mailing_campaign c
                ON (c.id = s.mass_mailing_campaign_id)
            WHERE
                c.id IN %s
            GROUP BY
                c.id
        """, (tuple(self.ids), ))

        for row in self.env.cr.dictfetchall():
            total = row['total'] or 1
            row['delivered'] = row['sent'] - row['bounced']
            row['received_ratio'] = 100.0 * row['delivered'] / total
            row['opened_ratio'] = 100.0 * row['opened'] / total
            row['replied_ratio'] = 100.0 * row['replied'] / total
            row['bounced_ratio'] = 100.0 * row['bounced'] / total
            self.browse(row.pop('campaign_id')).update(row)

    def _compute_total_mailings(self):
        campaign_data = self.env['mail.mass_mailing'].read_group(
            [('mass_mailing_campaign_id', 'in', self.ids)],
            ['mass_mailing_campaign_id'], ['mass_mailing_campaign_id'])
        mapped_data = dict([(c['mass_mailing_campaign_id'][0], c['mass_mailing_campaign_id_count']) for c in campaign_data])
        for campaign in self:
            campaign.total_mailings = mapped_data.get(campaign.id, 0)

    def get_recipients(self, model=None):
        """Return the recipients of a mailing campaign. This is based on the statistics
        build for each mailing. """
        res = dict.fromkeys(self.ids, {})
        for campaign in self:
            domain = [('mass_mailing_campaign_id', '=', campaign.id)]
            if model:
                domain += [('model', '=', model)]
            res[campaign.id] = set(self.env['mail.mail.statistics'].search(domain).mapped('res_id'))
        return res

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """ Override read_group to always display all states. """
        if groupby and groupby[0] == "stage_id":
            # Default result structure
            states_read = self.env['mail.mass_mailing.stage'].search_read([], ['name'])
            states = [(state['id'], state['name']) for state in states_read]
            read_group_all_states = [{
                '__context': {'group_by': groupby[1:]},
                '__domain': domain + [('stage_id', '=', state_value)],
                'stage_id': state_value,
                'state_count': 0,
            } for state_value, state_name in states]
            # Get standard results
            read_group_res = super(MassMailingCampaign, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby)
            # Update standard results with default results
            result = []
            for state_value, state_name in states:
                res = [x for x in read_group_res if x['stage_id'] == (state_value, state_name)]
                if not res:
                    res = [x for x in read_group_all_states if x['stage_id'] == state_value]
                res[0]['stage_id'] = [state_value, state_name]
                result.append(res[0])
            return result
        else:
            return super(MassMailingCampaign, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby)


class MassMailing(models.Model):
    """ MassMailing models a wave of emails for a mass mailign campaign.
    A mass mailing is an occurence of sending emails. """

    _name = 'mail.mass_mailing'
    _description = 'Mass Mailing'
    # number of periods for tracking mail_mail statistics
    _period_number = 6
    _order = 'sent_date DESC'
    _inherits = {'utm.source': 'source_id'}
    _rec_name = "source_id"

    @api.model
    def default_get(self, fields):
        res = super(MassMailing, self).default_get(fields)
        if 'reply_to_mode' in fields and not 'reply_to_mode' in res and res.get('mailing_model_real'):
            if res['mailing_model_real'] in ['res.partner', 'mail.mass_mailing.contact']:
                res['reply_to_mode'] = 'email'
            else:
                res['reply_to_mode'] = 'thread'
        return res

    def _get_mailing_model(self):
        res = []
        for model_name in self.env:
            model = self.env[model_name]
            if hasattr(model, '_mail_mass_mailing') and getattr(model, '_mail_mass_mailing'):
                if getattr(model, 'message_mass_mailing_enabled'):
                    res.append((model._name, model.message_mass_mailing_enabled()))
                else:
                    res.append((model._name, model._mail_mass_mailing))
        res.append(('mail.mass_mailing.contact', _('Mail Contacts')))
        res.append(('mail.mass_mailing.list', _('Mailing List')))
        return res

    # indirections for inheritance
    _mailing_model = lambda self: self._get_mailing_model()

    active = fields.Boolean(default=True)
    email_from = fields.Char(string='From', required=True,
        default=lambda self: self.env['mail.message']._get_default_from())
    create_date = fields.Datetime(string='Creation Date')
    sent_date = fields.Datetime(string='Sent Date', oldname='date', copy=False)
    schedule_date = fields.Datetime(string='Schedule in the Future')
    body_html = fields.Html(string='Body', translate=html_translate, sanitize_attributes=False)
    attachment_ids = fields.Many2many('ir.attachment', 'mass_mailing_ir_attachments_rel',
        'mass_mailing_id', 'attachment_id', string='Attachments')
    keep_archives = fields.Boolean(string='Keep Archives')
    mass_mailing_campaign_id = fields.Many2one('mail.mass_mailing.campaign', string='Mass Mailing Campaign')
    campaign_id = fields.Many2one('utm.campaign', string='Campaign',
                                  help="This name helps you tracking your different campaign efforts, e.g. Fall_Drive, Christmas_Special")
    source_id = fields.Many2one('utm.source', string='Subject', required=True, ondelete='cascade',
                                help="This is the link source, e.g. Search Engine, another domain, or name of email list")
    medium_id = fields.Many2one('utm.medium', string='Medium',
                                help="This is the delivery method, e.g. Postcard, Email, or Banner Ad", default=lambda self: self.env.ref('utm.utm_medium_email'))
    clicks_ratio = fields.Integer(compute="_compute_clicks_ratio", string="Number of Clicks")
    state = fields.Selection([('draft', 'Draft'), ('in_queue', 'In Queue'), ('sending', 'Sending'), ('done', 'Sent')],
        string='Status', required=True, copy=False, default='draft')
    color = fields.Integer(string='Color Index')
    # mailing options
    reply_to_mode = fields.Selection(
        [('thread', 'Followers of leads/applicants'), ('email', 'Specified Email Address')],
        string='Reply-To Mode', required=True)
    reply_to = fields.Char(string='Reply To', help='Preferred Reply-To Address',
        default=lambda self: self.env['mail.message']._get_default_from())
    # recipients
    mailing_model_real = fields.Char(compute='_compute_model', string='Recipients Real Model', default='mail.mass_mailing.contact', required=True)
    mailing_model = fields.Selection(selection=_mailing_model, string='Recipients Model', default='mail.mass_mailing.list')
    mailing_domain = fields.Char(string='Domain', oldname='domain', default=[])
    contact_list_ids = fields.Many2many('mail.mass_mailing.list', 'mail_mass_mailing_list_rel',
        string='Mailing Lists')
    contact_ab_pc = fields.Integer(string='A/B Testing percentage',
        help='Percentage of the contacts that will be mailed. Recipients will be taken randomly.', default=100)
    # statistics data
    statistics_ids = fields.One2many('mail.mail.statistics', 'mass_mailing_id', string='Emails Statistics')
    total = fields.Integer(compute="_compute_total")
    scheduled = fields.Integer(compute="_compute_statistics")
    failed = fields.Integer(compute="_compute_statistics")
    sent = fields.Integer(compute="_compute_statistics")
    delivered = fields.Integer(compute="_compute_statistics")
    opened = fields.Integer(compute="_compute_statistics")
    replied = fields.Integer(compute="_compute_statistics")
    bounced = fields.Integer(compute="_compute_statistics")
    failed = fields.Integer(compute="_compute_statistics")
    received_ratio = fields.Integer(compute="_compute_statistics", string='Received Ratio')
    opened_ratio = fields.Integer(compute="_compute_statistics", string='Opened Ratio')
    replied_ratio = fields.Integer(compute="_compute_statistics", string='Replied Ratio')
    bounced_ratio = fields.Integer(compute="_compute_statistics", String='Bounced Ratio')
    next_departure = fields.Datetime(compute="_compute_next_departure", string='Next Departure')

    def _compute_total(self):
        for mass_mailing in self:
            mass_mailing.total = len(mass_mailing.sudo().get_recipients())

    def _compute_clicks_ratio(self):
        self.env.cr.execute("""
            SELECT COUNT(DISTINCT(stats.id)) AS nb_mails, COUNT(DISTINCT(clicks.mail_stat_id)) AS nb_clicks, stats.mass_mailing_id AS id
            FROM mail_mail_statistics AS stats
            LEFT OUTER JOIN link_tracker_click AS clicks ON clicks.mail_stat_id = stats.id
            WHERE stats.mass_mailing_id IN %s
            GROUP BY stats.mass_mailing_id
        """, (tuple(self.ids), ))

        mass_mailing_data = self.env.cr.dictfetchall()
        mapped_data = dict([(m['id'], 100 * m['nb_clicks'] / m['nb_mails']) for m in mass_mailing_data])
        for mass_mailing in self:
            mass_mailing.clicks_ratio = mapped_data.get(mass_mailing.id, 0)

    @api.depends('mailing_model')
    def _compute_model(self):
        for record in self:
            record.mailing_model_real = (record.mailing_model != 'mail.mass_mailing.list') and record.mailing_model or 'mail.mass_mailing.contact'

    def _compute_statistics(self):
        """ Compute statistics of the mass mailing """
        self.env.cr.execute("""
            SELECT
                m.id as mailing_id,
                COUNT(s.id) AS total,
                COUNT(CASE WHEN s.sent is not null THEN 1 ELSE null END) AS sent,
                COUNT(CASE WHEN s.scheduled is not null AND s.sent is null AND s.exception is null THEN 1 ELSE null END) AS scheduled,
                COUNT(CASE WHEN s.scheduled is not null AND s.sent is null AND s.exception is not null THEN 1 ELSE null END) AS failed,
                COUNT(CASE WHEN s.sent is not null AND s.bounced is null THEN 1 ELSE null END) AS delivered,
                COUNT(CASE WHEN s.opened is not null THEN 1 ELSE null END) AS opened,
                COUNT(CASE WHEN s.replied is not null THEN 1 ELSE null END) AS replied,
                COUNT(CASE WHEN s.bounced is not null THEN 1 ELSE null END) AS bounced,
                COUNT(CASE WHEN s.exception is not null THEN 1 ELSE null END) AS failed
            FROM
                mail_mail_statistics s
            RIGHT JOIN
                mail_mass_mailing m
                ON (m.id = s.mass_mailing_id)
            WHERE
                m.id IN %s
            GROUP BY
                m.id
        """, (tuple(self.ids), ))
        for row in self.env.cr.dictfetchall():
            total = row.pop('total') or 1
            row['received_ratio'] = 100.0 * row['delivered'] / total
            row['opened_ratio'] = 100.0 * row['opened'] / total
            row['replied_ratio'] = 100.0 * row['replied'] / total
            row['bounced_ratio'] = 100.0 * row['bounced'] / total
            self.browse(row.pop('mailing_id')).update(row)

    @api.multi
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
        secret = self.env["ir.config_parameter"].sudo().get_param(
            "database.secret")
        token = (self.env.cr.dbname, self.id, int(res_id), tools.ustr(email))
        return hmac.new(str(secret), repr(token), hashlib.sha512).hexdigest()

    def _compute_next_departure(self):
        cron_next_call = self.env.ref('mass_mailing.ir_cron_mass_mailing_queue').sudo().nextcall
        for mass_mailing in self:
            schedule_date = mass_mailing.schedule_date
            if schedule_date:
                if datetime.now() > fields.Datetime.from_string(schedule_date):
                    mass_mailing.next_departure = cron_next_call
                else:
                    mass_mailing.next_departure = schedule_date
            else:
                mass_mailing.next_departure = cron_next_call

    @api.onchange('mass_mailing_campaign_id')
    def _onchange_mass_mailing_campaign_id(self):
        if self.mass_mailing_campaign_id:
            dic = {'campaign_id': self.mass_mailing_campaign_id.campaign_id,
                   'source_id': self.mass_mailing_campaign_id.source_id,
                   'medium_id': self.mass_mailing_campaign_id.medium_id}
            self.update(dic)

    @api.onchange('mailing_model', 'contact_list_ids')
    def _onchange_model_and_list(self):
        if self.mailing_model == 'mail.mass_mailing.list':
            if self.contact_list_ids:
                self.mailing_domain = "[('list_ids', 'in', [%s]), ('opt_out', '=', False)]" % (','.join(str(id) for id in self.contact_list_ids.ids),)
            else:
                self.mailing_domain = "[(0, '=', 1)]"
        elif 'opt_out' in self.env[self.mailing_model]._fields and not self.mailing_domain:
            self.mailing_domain = "[('opt_out', '=', False)]"
        self.body_html = "on_change_model_and_list"

    #------------------------------------------------------
    # Technical stuff
    #------------------------------------------------------

    @api.model
    def name_create(self, name):
        """ _rec_name is source_id, creates a utm.source instead """
        mass_mailing = self.create({'name': name})
        return mass_mailing.name_get()[0]

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {},
                       name=_('%s (copy)') % self.name)
        return super(MassMailing, self).copy(default=default)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """ Override read_group to always display all states. """
        if groupby and groupby[0] == "state":
            # Default result structure
            states = [('draft', _('Draft')), ('in_queue', _('In Queue')), ('sending', _('Sending')), ('done', _('Sent'))]
            read_group_all_states = [{
                '__context': {'group_by': groupby[1:]},
                '__domain': domain + [('state', '=', state_value)],
                'state': state_value,
                'state_count': 0,
            } for state_value, state_name in states]
            # Get standard results
            read_group_res = super(MassMailing, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby)
            # Update standard results with default results
            result = []
            for state_value, state_name in states:
                res = [x for x in read_group_res if x['state'] == state_value]
                if not res:
                    res = [x for x in read_group_all_states if x['state'] == state_value]
                res[0]['state'] = [state_value, state_name]
                result.append(res[0])
            return result
        else:
            return super(MassMailing, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby)

    def update_opt_out(self, email, res_ids, value):
        model = self.env[self.mailing_model_real].with_context(active_test=False)
        if 'opt_out' in model._fields:
            email_fname = 'email_from'
            if 'email' in model._fields:
                email_fname = 'email'
            records = model.search([('id', 'in', res_ids), (email_fname, 'ilike', email)])
            records.write({'opt_out': value})

    #------------------------------------------------------
    # Views & Actions
    #------------------------------------------------------

    @api.multi
    def action_duplicate(self):
        self.ensure_one()
        mass_mailing_copy = self.copy()
        if mass_mailing_copy:
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'mail.mass_mailing',
                'res_id': mass_mailing_copy.id,
                'context': self.env.context,
                'flags': {'initial_mode': 'edit'},
            }
        return False

    @api.multi
    def action_test_mailing(self):
        self.ensure_one()
        ctx = dict(self.env.context, default_mass_mailing_id=self.id)
        return {
            'name': _('Test Mailing'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.mass_mailing.test',
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def put_in_queue(self):
        self.write({'sent_date': fields.Datetime.now(), 'state': 'in_queue'})

    @api.multi
    def cancel_mass_mailing(self):
        self.write({'state': 'draft'})

    @api.multi
    def retry_failed_mail(self):
        failed_mails = self.env['mail.mail'].search([('mailing_id', 'in', self.ids), ('state', '=', 'exception')])
        failed_mails.mapped('statistics_ids').unlink()
        failed_mails.unlink()
        self.write({'state': 'in_queue'})

    #------------------------------------------------------
    # Email Sending
    #------------------------------------------------------

    def _get_blacklist(self):
        """Returns a set of emails opted-out in target model"""
        # TODO: implement a global blacklist table, to easily share
        # it and update it.
        self.ensure_one()
        blacklist = {}
        target = self.env[self.mailing_model_real]
        mail_field = 'email' if 'email' in target._fields else 'email_from'
        if 'opt_out' in target._fields:
            # avoid loading a large number of records in memory
            # + use a basic heuristic for extracting emails
            query = """
                SELECT lower(substring(%(mail_field)s, '([^ ,;<@]+@[^> ,;]+)'))
                  FROM %(target)s
                 WHERE opt_out AND
                       substring(%(mail_field)s, '([^ ,;<@]+@[^> ,;]+)') IS NOT NULL;
            """
            query = query % {'target': target._table, 'mail_field': mail_field}
            self._cr.execute(query)
            blacklist = set(m[0] for m in self._cr.fetchall())
            _logger.info(
                "Mass-mailing %s targets %s, blacklist: %s emails",
                self, target._name, len(blacklist))
        else:
            _logger.info("Mass-mailing %s targets %s, no blacklist available", self, target._name)
        return blacklist

    def _get_seen_list(self):
        """Returns a set of emails already targeted by current mailing/campaign (no duplicates)"""
        self.ensure_one()
        target = self.env[self.mailing_model_real]
        mail_field = 'email' if 'email' in target._fields else 'email_from'
        # avoid loading a large number of records in memory
        # + use a basic heuristic for extracting emails
        query = """
            SELECT lower(substring(%(mail_field)s, '([^ ,;<@]+@[^> ,;]+)'))
              FROM mail_mail_statistics s
              JOIN %(target)s t ON (s.res_id = t.id)
             WHERE substring(%(mail_field)s, '([^ ,;<@]+@[^> ,;]+)') IS NOT NULL
        """
        if self.mass_mailing_campaign_id.unique_ab_testing:
            query +="""
               AND s.mass_mailing_campaign_id = %%(mailing_campaign_id)s;
            """
        else:
            query +="""
               AND s.mass_mailing_id = %%(mailing_id)s;
            """
        query = query % {'target': target._table, 'mail_field': mail_field}
        params = {'mailing_id': self.id, 'mailing_campaign_id': self.mass_mailing_campaign_id.id}
        self._cr.execute(query, params)
        seen_list = set(m[0] for m in self._cr.fetchall())
        _logger.info(
            "Mass-mailing %s has already reached %s %s emails", self, len(seen_list), target._name)
        return seen_list

    def _get_mass_mailing_context(self):
        """Returns extra context items with pre-filled blacklist and seen list for massmailing"""
        return {
            'mass_mailing_blacklist': self._get_blacklist(),
            'mass_mailing_seen_list': self._get_seen_list(),
        }

    def get_recipients(self):
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
                already_mailed = self.mass_mailing_campaign_id.get_recipients()[self.mass_mailing_campaign_id.id]
            else:
                already_mailed = set([])
            remaining = set(res_ids).difference(already_mailed)
            if topick > len(remaining):
                topick = len(remaining)
            res_ids = random.sample(remaining, topick)
        return res_ids

    def get_remaining_recipients(self):
        res_ids = self.get_recipients()
        already_mailed = self.env['mail.mail.statistics'].search_read([('model', '=', self.mailing_model_real),
                                                                     ('res_id', 'in', res_ids),
                                                                     ('mass_mailing_id', '=', self.id)], ['res_id'])
        already_mailed_res_ids = [record['res_id'] for record in already_mailed]
        return list(set(res_ids) - set(already_mailed_res_ids))

    def send_mail(self):
        author_id = self.env.user.partner_id.id
        for mailing in self:
            # instantiate an email composer + send emails
            res_ids = mailing.get_remaining_recipients()
            if not res_ids:
                raise UserError(_('Please select recipients.'))

            # Convert links in absolute URLs before the application of the shortener
            mailing.body_html = self.env['mail.template']._replace_local_links(mailing.body_html)

            composer_values = {
                'author_id': author_id,
                'attachment_ids': [(4, attachment.id) for attachment in mailing.attachment_ids],
                'body': mailing.convert_links()[mailing.id],
                'subject': mailing.name,
                'model': mailing.mailing_model_real,
                'email_from': mailing.email_from,
                'record_name': False,
                'composition_mode': 'mass_mail',
                'mass_mailing_id': mailing.id,
                'mailing_list_ids': [(4, l.id) for l in mailing.contact_list_ids],
                'no_auto_thread': mailing.reply_to_mode != 'thread',
            }
            if mailing.reply_to_mode == 'email':
                composer_values['reply_to'] = mailing.reply_to

            composer = self.env['mail.compose.message'].with_context(active_ids=res_ids).create(composer_values)
            extra_context = self._get_mass_mailing_context()
            composer = composer.with_context(active_ids=res_ids, **extra_context)
            composer.send_mail(auto_commit=True)
            mailing.state = 'done'
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
            if len(mass_mailing.get_remaining_recipients()) > 0:
                mass_mailing.state = 'sending'
                mass_mailing.send_mail()
            else:
                mass_mailing.state = 'done'
