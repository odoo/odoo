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
    'mail.mass_mailing.list',
]
EMAIL_PATTERN = '([^ ,;<@]+@[^> ,;]+)'

# Syntax of the data URL Scheme: https://tools.ietf.org/html/rfc2397#section-3
# Used to find inline images
image_re = re.compile(r"data:(image/[A-Za-z]+);base64,(.*)")


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

class MassMailingContactListRel(models.Model):
    """ Intermediate model between mass mailing list and mass mailing contact
        Indicates if a contact is opted out for a particular list
    """
    _name = 'mail.mass_mailing.list_contact_rel'
    _description = 'Mass Mailing Subscription Information'
    _table = 'mail_mass_mailing_contact_list_rel'
    _rec_name = 'contact_id'

    contact_id = fields.Many2one('mail.mass_mailing.contact', string='Contact', ondelete='cascade', required=True)
    list_id = fields.Many2one('mail.mass_mailing.list', string='Mailing List', ondelete='cascade', required=True)
    opt_out = fields.Boolean(string='Opt Out',
                             help='The contact has chosen not to receive mails anymore from this list', default=False)
    unsubscription_date = fields.Datetime(string='Unsubscription Date')
    contact_count = fields.Integer(related='list_id.contact_nbr', store=False, readonly=False)
    message_bounce = fields.Integer(related='contact_id.message_bounce', store=False, readonly=False)
    is_blacklisted = fields.Boolean(related='contact_id.is_blacklisted', store=False, readonly=False)

    _sql_constraints = [
        ('unique_contact_list', 'unique (contact_id, list_id)',
         'A contact cannot be subscribed multiple times to the same list!')
    ]

    @api.model
    def create(self, vals):
        if 'opt_out' in vals:
            vals['unsubscription_date'] = vals['opt_out'] and fields.Datetime.now()
        return super(MassMailingContactListRel, self).create(vals)

    @api.multi
    def write(self, vals):
        if 'opt_out' in vals:
            vals['unsubscription_date'] = vals['opt_out'] and fields.Datetime.now()
        return super(MassMailingContactListRel, self).write(vals)

    def action_open_mailing_list_contact(self):
        """TODO DBE : To remove - Deprecated"""
        contact_id = self.contact_id
        action = {
            'name': _(contact_id.name),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.mass_mailing.contact',
            'view_mode': 'form',
            'target': 'current',
            'res_id': contact_id.id
        }
        return action


class MassMailingList(models.Model):
    """Model of a contact list. """
    _name = 'mail.mass_mailing.list'
    _order = 'name'
    _description = 'Mailing List'

    name = fields.Char(string='Mailing List', required=True)
    active = fields.Boolean(default=True)
    contact_nbr = fields.Integer(compute="_compute_contact_nbr", string='Number of Contacts')
    contact_ids = fields.Many2many(
        'mail.mass_mailing.contact', 'mail_mass_mailing_contact_list_rel', 'list_id', 'contact_id',
        string='Mailing Lists')
    subscription_contact_ids = fields.One2many('mail.mass_mailing.list_contact_rel', 'list_id',
        string='Subscription Information')
    is_public = fields.Boolean(default=True, help="The mailing list can be accessible by recipient in the unsubscription"
                                                  " page to allows him to update his subscription preferences.")

    # Compute number of contacts non opt-out, non blacklisted and valid email recipient for a mailing list
    def _compute_contact_nbr(self):
        self.env.cr.execute('''
            select
                list_id, count(*)
            from
                mail_mass_mailing_contact_list_rel r
                left join mail_mass_mailing_contact c on (r.contact_id=c.id)
                left join mail_blacklist bl on (LOWER(substring(c.email, %s)) = bl.email and bl.active)
            where
                list_id in %s AND
                COALESCE(r.opt_out,FALSE) = FALSE
                AND c.email IS NOT NULL
                AND bl.id IS NULL
            group by
                list_id
        ''', [EMAIL_PATTERN, tuple(self.ids)])
        data = dict(self.env.cr.fetchall())
        for mailing_list in self:
            mailing_list.contact_nbr = data.get(mailing_list.id, 0)

    @api.multi
    def write(self, vals):
        # Prevent archiving used mailing list
        if 'active' in vals and not vals.get('active'):
            mass_mailings = self.env['mail.mass_mailing'].search_count([
                ('state', '!=', 'done'),
                ('contact_list_ids', 'in', self.ids),
            ])

            if mass_mailings > 0:
                raise UserError(_("At least one of the mailing list you are trying to archive is used in an ongoing mailing campaign."))

        return super(MassMailingList, self).write(vals)

    @api.multi
    def name_get(self):
        return [(list.id, "%s (%s)" % (list.name, list.contact_nbr)) for list in self]

    @api.multi
    def action_merge(self, src_lists, archive):
        """
            Insert all the contact from the mailing lists 'src_lists' to the
            mailing list in 'self'. Possibility to archive the mailing lists
            'src_lists' after the merge except the destination mailing list 'self'.
        """
        # Explation of the SQL query with an example. There are the following lists
        # A (id=4): yti@odoo.com; yti@example.com
        # B (id=5): yti@odoo.com; yti@openerp.com
        # C (id=6): nothing
        # To merge the mailing lists A and B into C, we build the view st that looks
        # like this with our example:
        #
        #  contact_id |           email           | row_number |  list_id |
        # ------------+---------------------------+------------------------
        #           4 | yti@odoo.com              |          1 |        4 |
        #           6 | yti@odoo.com              |          2 |        5 |
        #           5 | yti@example.com           |          1 |        4 |
        #           7 | yti@openerp.com           |          1 |        5 |
        #
        # The row_column is kind of an occurence counter for the email address.
        # Then we create the Many2many relation between the destination list and the contacts
        # while avoiding to insert an existing email address (if the destination is in the source
        # for example)
        self.ensure_one()
        # Put destination is sources lists if not already the case
        src_lists |= self
        self.env.cr.execute("""
            INSERT INTO mail_mass_mailing_contact_list_rel (contact_id, list_id)
            SELECT st.contact_id AS contact_id, %s AS list_id
            FROM
                (
                SELECT
                    contact.id AS contact_id,
                    contact.email AS email,
                    mailing_list.id AS list_id,
                    row_number() OVER (PARTITION BY email ORDER BY email) AS rn
                FROM
                    mail_mass_mailing_contact contact,
                    mail_mass_mailing_contact_list_rel contact_list_rel,
                    mail_mass_mailing_list mailing_list
                WHERE contact.id=contact_list_rel.contact_id
                AND COALESCE(contact_list_rel.opt_out,FALSE) = FALSE
                AND LOWER(substring(contact.email, %s)) NOT IN (select email from mail_blacklist where active = TRUE)
                AND mailing_list.id=contact_list_rel.list_id
                AND mailing_list.id IN %s
                AND NOT EXISTS
                    (
                    SELECT 1
                    FROM
                        mail_mass_mailing_contact contact2,
                        mail_mass_mailing_contact_list_rel contact_list_rel2
                    WHERE contact2.email = contact.email
                    AND contact_list_rel2.contact_id = contact2.id
                    AND contact_list_rel2.list_id = %s
                    )
                ) st
            WHERE st.rn = 1;""", (self.id, EMAIL_PATTERN, tuple(src_lists.ids), self.id))
        self.invalidate_cache()
        if archive:
            (src_lists - self).write({'active': False})

    @api.multi
    def close_dialog(self):
        return {'type': 'ir.actions.act_window_close'}


class MassMailingContact(models.Model):
    """Model of a contact. This model is different from the partner model
    because it holds only some basic information: name, email. The purpose is to
    be able to deal with large contact list to email without bloating the partner
    base."""
    _name = 'mail.mass_mailing.contact'
    _inherit = ['mail.thread', 'mail.blacklist.mixin']
    _description = 'Mass Mailing Contact'
    _order = 'email'
    _rec_name = 'email'

    name = fields.Char()
    company_name = fields.Char(string='Company Name')
    title_id = fields.Many2one('res.partner.title', string='Title')
    email = fields.Char(required=True)
    is_email_valid = fields.Boolean(compute='_compute_is_email_valid', store=True)
    list_ids = fields.Many2many(
        'mail.mass_mailing.list', 'mail_mass_mailing_contact_list_rel',
        'contact_id', 'list_id', string='Mailing Lists')
    subscription_list_ids = fields.One2many('mail.mass_mailing.list_contact_rel',
        'contact_id', string='Subscription Information')
    message_bounce = fields.Integer(string='Bounced', help='Counter of the number of bounced emails for this contact.', default=0)
    country_id = fields.Many2one('res.country', string='Country')
    tag_ids = fields.Many2many('res.partner.category', string='Tags')
    opt_out = fields.Boolean('Opt Out', compute='_compute_opt_out', search='_search_opt_out',
                             help='Opt out flag for a specific mailing list.'
                                  'This field should not be used in a view without a unique and active mailing list context.')

    @api.depends('email')
    def _compute_is_email_valid(self):
        for record in self:
            record.is_email_valid = re.match(EMAIL_PATTERN, record.email)

    @api.model
    def _search_opt_out(self, operator, value):
        # Assumes operator is '=' or '!=' and value is True or False
        if operator != '=':
            if operator == '!=' and isinstance(value, bool):
                value = not value
            else:
                raise NotImplementedError()

        if 'default_list_ids' in self._context and isinstance(self._context['default_list_ids'], (list, tuple)) and len(self._context['default_list_ids']) == 1:
            [active_list_id] = self._context['default_list_ids']
            contacts = self.env['mail.mass_mailing.list_contact_rel'].search([('list_id', '=', active_list_id)])
            return [('id', 'in', [record.contact_id.id for record in contacts if record.opt_out == value])]
        else:
            raise UserError(_('Search opt out cannot be executed without a unique and valid active mailing list context.'))

    @api.depends('subscription_list_ids')
    def _compute_opt_out(self):
        if 'default_list_ids' in self._context and isinstance(self._context['default_list_ids'], (list, tuple)) and len(self._context['default_list_ids']) == 1:
            [active_list_id] = self._context['default_list_ids']
            for record in self:
                active_subscription_list = record.subscription_list_ids.filtered(lambda l: l.list_id.id == active_list_id)
                record.opt_out = active_subscription_list.opt_out
        else:
            for record in self:
                record.opt_out = False

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

    stage_id = fields.Many2one('mail.mass_mailing.stage', string='Stage', ondelete='restrict', required=True, 
        default=lambda self: self.env['mail.mass_mailing.stage'].search([], limit=1),
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
        'mail.mass_mailing.tag', 'mail_mass_mailing_tag_rel',
        'tag_id', 'campaign_id', string='Tags')
    mass_mailing_ids = fields.One2many(
        'mail.mass_mailing', 'mass_mailing_campaign_id',
        string='Mass Mailings')
    unique_ab_testing = fields.Boolean(string='Allow A/B Testing', default=False,
        help='If checked, recipients will be mailed only once for the whole campaign. '
             'This lets you send different mailings to randomly selected recipients and test '
             'the effectiveness of the mailings, without causing duplicate messages.')
    color = fields.Integer(string='Color Index')
    clicks_ratio = fields.Integer(compute="_compute_clicks_ratio", string="Number of clicks")
    # stat fields
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
                COUNT(CASE WHEN s.scheduled is not null AND s.sent is null AND s.exception is null AND s.ignored is null THEN 1 ELSE null END) AS scheduled,
                COUNT(CASE WHEN s.scheduled is not null AND s.sent is null AND s.exception is not null THEN 1 ELSE null END) AS failed,
                COUNT(CASE WHEN s.scheduled is not null AND s.sent is null AND s.exception is null AND s.ignored is not null THEN 1 ELSE null END) AS ignored,
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
            total = (row['total'] - row['ignored']) or 1
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
    def _group_expand_stage_ids(self, stages, domain, order):
        """ Read group customization in order to display all the stages in the
            kanban view, even if they are empty
        """
        stage_ids = stages._search([], order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)


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
            if res['mailing_model_real'] in ['res.partner', 'mail.mass_mailing.contact']:
                res['reply_to_mode'] = 'email'
            else:
                res['reply_to_mode'] = 'thread'
        return res

    active = fields.Boolean(default=True)
    email_from = fields.Char(string='From', required=True,
        default=lambda self: self.env['mail.message']._get_default_from())
    sent_date = fields.Datetime(string='Sent Date', oldname='date', copy=False)
    schedule_date = fields.Datetime(string='Schedule in the Future')
    body_html = fields.Html(string='Body', sanitize_attributes=False)
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
        string='Status', required=True, copy=False, default='draft', group_expand='_group_expand_states')
    color = fields.Integer(string='Color Index')
    user_id = fields.Many2one('res.users', string='Mailing Manager', default=lambda self: self.env.user)
    # mailing options
    reply_to_mode = fields.Selection(
        [('thread', 'Recipient Followers'), ('email', 'Specified Email Address')], string='Reply-To Mode', required=True)
    reply_to = fields.Char(string='Reply To', help='Preferred Reply-To Address',
        default=lambda self: self.env['mail.message']._get_default_from())
    # recipients
    mailing_model_real = fields.Char(compute='_compute_model', string='Recipients Real Model', default='mail.mass_mailing.contact', required=True)
    mailing_model_id = fields.Many2one('ir.model', string='Recipients Model', domain=[('model', 'in', MASS_MAILING_BUSINESS_MODELS)],
        default=lambda self: self.env.ref('mass_mailing.model_mail_mass_mailing_list').id)
    mailing_model_name = fields.Char(related='mailing_model_id.model', string='Recipients Model Name', readonly=True, related_sudo=True)
    mailing_domain = fields.Char(string='Domain', oldname='domain', default=[])
    mail_server_id = fields.Many2one('ir.mail_server', string='Mail Server',
        default=_get_default_mail_server_id,
        help="Use a specific mail server in priority. Otherwise Odoo relies on the first outgoing mail server available (based on their sequencing) as it does for normal mails.")
    contact_list_ids = fields.Many2many('mail.mass_mailing.list', 'mail_mass_mailing_list_rel',
        string='Mailing Lists')
    contact_ab_pc = fields.Integer(string='A/B Testing percentage',
        help='Percentage of the contacts that will be mailed. Recipients will be taken randomly.', default=100)
    # statistics data
    statistics_ids = fields.One2many('mail.mail.statistics', 'mass_mailing_id', string='Emails Statistics')
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

    @api.depends('mailing_model_id')
    def _compute_model(self):
        for record in self:
            record.mailing_model_real = (record.mailing_model_name != 'mail.mass_mailing.list') and record.mailing_model_name or 'mail.mass_mailing.contact'

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
            total = row['expected'] = (row['expected'] - row['ignored']) or 1
            row['received_ratio'] = 100.0 * row['delivered'] / total
            row['opened_ratio'] = 100.0 * row['opened'] / total
            row['clicks_ratio'] = 100.0 * row['clicked'] / total
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
        return hmac.new(secret.encode('utf-8'), repr(token).encode('utf-8'), hashlib.sha512).hexdigest()

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
            dic = {'campaign_id': self.mass_mailing_campaign_id.campaign_id,
                   'source_id': self.mass_mailing_campaign_id.source_id,
                   'medium_id': self.mass_mailing_campaign_id.medium_id}
            self.update(dic)

    @api.onchange('mailing_model_id', 'contact_list_ids')
    def _onchange_model_and_list(self):
        mailing_domain = []
        if self.mailing_model_name:
            if self.mailing_model_name == 'mail.mass_mailing.list':
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
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        # Cleaning archived contact_list_ids
        default = dict(default or {},
                       name=_('%s (copy)') % self.name,
                       contact_list_ids=self.contact_list_ids.ids)
        res = super(MassMailing, self).copy(default=default)
        # Re-evaluating the domain
        body_html = res.body_html
        res._onchange_model_and_list()
        res.body_html = body_html
        return res

    def _group_expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

    def update_opt_out(self, email, list_ids, value):
        if len(list_ids) > 0:
            model = self.env['mail.mass_mailing.contact'].with_context(active_test=False)
            records = model.search([('email', '=ilike', email)])
            opt_out_records = self.env['mail.mass_mailing.list_contact_rel'].search([
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

    @api.model
    def create(self, values):
        if values.get('body_html'):
            values['body_html'] = self._convert_inline_images_to_urls(values['body_html'])
        return super(MassMailing, self).create(values)

    def write(self, values):
        if values.get('body_html'):
            values['body_html'] = self._convert_inline_images_to_urls(values['body_html'])
        return super(MassMailing, self).write(values)

    def _convert_inline_images_to_urls(self, body_html):
        """
        Find inline base64 encoded images, make an attachement out of
        them and replace the inline image with an url to the attachement.
        """

        def _image_to_url(b64image: bytes):
            """Store an image in an attachement and returns an url"""
            attachment = self.env['ir.attachment'].create({
                'name': "cropped_image",
                'datas': b64image,
                'datas_fname': "cropped_image_mailing_{}".format(self.id),
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

    #------------------------------------------------------
    # Views & Actions
    #------------------------------------------------------

    @api.multi
    def action_duplicate(self):
        self.ensure_one()
        mass_mailing_copy = self.copy()
        if mass_mailing_copy:
            context = dict(self.env.context)
            context['form_view_initial_mode'] = 'edit'
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'mail.mass_mailing',
                'res_id': mass_mailing_copy.id,
                'context': context,
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
    def action_schedule_date(self):
        self.ensure_one()
        action = self.env.ref('mass_mailing.mass_mailing_schedule_date_action').read()[0]
        action['context'] = dict(self.env.context, default_mass_mailing_id=self.id)
        return action

    @api.multi
    def put_in_queue(self):
        self.write({'state': 'in_queue'})

    @api.multi
    def cancel_mass_mailing(self):
        self.write({'state': 'draft', 'schedule_date': False})

    @api.multi
    def retry_failed_mail(self):
        failed_mails = self.env['mail.mail'].search([('mailing_id', 'in', self.ids), ('state', '=', 'exception')])
        failed_mails.mapped('statistics_ids').unlink()
        failed_mails.sudo().unlink()
        res_ids = self.get_recipients()
        except_mailed = self.env['mail.mail.statistics'].search([
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
            opened_stats = self.statistics_ids.filtered(lambda stat: stat[view_filter])
        elif view_filter == ('delivered'):
            opened_stats = self.statistics_ids.filtered(lambda stat: stat.sent and not stat.bounced)
        else:
            opened_stats = self.env['mail.mail.statistics']
        res_ids = opened_stats.mapped('res_id')
        model_name = self.env['ir.model']._get(self.mailing_model_real).display_name
        return {
            'name': model_name,
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': self.mailing_model_real,
            'domain': [('id', 'in', res_ids)],
        }

    #------------------------------------------------------
    # Email Sending
    #------------------------------------------------------

    def _get_opt_out_list(self):
        """Returns a set of emails opted-out in target model"""
        self.ensure_one()
        opt_out = {}
        target = self.env[self.mailing_model_real]
        if self.mailing_model_real == "mail.mass_mailing.contact":
            # if user is opt_out on One list but not on another
            # or if two user with same email address, one opted in and the other one opted out, send the mail anyway
            # TODO DBE Fixme : Optimise the following to get real opt_out and opt_in
            target_list_contacts = self.env['mail.mass_mailing.list_contact_rel'].search(
                [('list_id', 'in', self.contact_list_ids.ids)])
            opt_out_contacts = target_list_contacts.filtered(lambda rel: rel.opt_out).mapped('contact_id.email')
            opt_in_contacts = target_list_contacts.filtered(lambda rel: not rel.opt_out).mapped('contact_id.email')
            normalized_email = [tools.email_split(c) for c in opt_out_contacts if c not in opt_in_contacts]
            opt_out = set(email[0].lower() for email in normalized_email if email)

            _logger.info(
                "Mass-mailing %s targets %s, blacklist: %s emails",
                self, target._name, len(opt_out))
        else:
            _logger.info("Mass-mailing %s targets %s, no opt out list available", self, target._name)
        return opt_out

    def _get_convert_links(self):
        self.ensure_one()
        utm_mixin = self.mass_mailing_campaign_id if self.mass_mailing_campaign_id else self
        vals = {'mass_mailing_id': self.id}

        if self.mass_mailing_campaign_id:
            vals['mass_mailing_campaign_id'] = self.mass_mailing_campaign_id.id
        if utm_mixin.campaign_id:
            vals['campaign_id'] = utm_mixin.campaign_id.id
        if utm_mixin.source_id:
            vals['source_id'] = utm_mixin.source_id.id
        if utm_mixin.medium_id:
            vals['medium_id'] = utm_mixin.medium_id.id
        return vals

    def _get_seen_list(self):
        """Returns a set of emails already targeted by current mailing/campaign (no duplicates)"""
        self.ensure_one()
        target = self.env[self.mailing_model_real]
        if set(['email', 'email_from']) & set(target._fields):
            mail_field = 'email' if 'email' in target._fields else 'email_from'
            # avoid loading a large number of records in memory
            # + use a basic heuristic for extracting emails
            query = """
                SELECT lower(substring(t.%(mail_field)s, '([^ ,;<@]+@[^> ,;]+)'))
                  FROM mail_mail_statistics s
                  JOIN %(target)s t ON (s.res_id = t.id)
                 WHERE substring(t.%(mail_field)s, '([^ ,;<@]+@[^> ,;]+)') IS NOT NULL
            """
        elif 'partner_id' in target._fields:
            mail_field = 'email'
            query = """
                SELECT lower(substring(p.%(mail_field)s, '([^ ,;<@]+@[^> ,;]+)'))
                  FROM mail_mail_statistics s
                  JOIN %(target)s t ON (s.res_id = t.id)
                  JOIN res_partner p ON (t.partner_id = p.id)
                 WHERE substring(p.%(mail_field)s, '([^ ,;<@]+@[^> ,;]+)') IS NOT NULL
            """
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

    def send_mail(self, res_ids=None):
        author_id = self.env.user.partner_id.id

        for mailing in self:
            if not res_ids:
                res_ids = mailing.get_remaining_recipients()
            if not res_ids:
                raise UserError(_('There is no recipients selected.'))

            composer_values = {
                'author_id': author_id,
                'attachment_ids': [(4, attachment.id) for attachment in mailing.attachment_ids],
                'body': mailing.body_html,
                'subject': mailing.name,
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
            mass_mailing = mass_mailing.with_context(**user.sudo(user=user).context_get())
            if len(mass_mailing.get_remaining_recipients()) > 0:
                mass_mailing.state = 'sending'
                mass_mailing.send_mail()
            else:
                mass_mailing.write({'state': 'done', 'sent_date': fields.Datetime.now()})
