# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailMailStats(models.Model):
    """ MailMailStats models the statistics collected about emails. Those statistics
    are stored in a separated model and table to avoid bloating the mail_mail table
    with statistics values. This also allows to delete emails send with mass mailing
    without loosing the statistics about them. """

    _name = 'mail.mail.statistics'
    _description = 'Email Statistics'
    _rec_name = 'message_id'
    _order = 'message_id'

    mail_mail_id = fields.Many2one('mail.mail', string='Mail', index=True)
    mail_mail_id_int = fields.Integer(
        string='Mail ID (tech)',
        help='ID of the related mail_mail. This field is an integer field because '
             'the related mail_mail can be deleted separately from its statistics. '
             'However the ID is needed for several action and controllers.',
        index=True,
    )
    message_id = fields.Char(string='Message-ID')
    model = fields.Char(string='Document model')
    res_id = fields.Integer(string='Document ID')
    # campaign / wave data
    mass_mailing_id = fields.Many2one('mail.mass_mailing', string='Mass Mailing')
    mass_mailing_campaign_id = fields.Many2one(
        related='mass_mailing_id.mass_mailing_campaign_id',
        string='Mass Mailing Campaign',
        store=True, readonly=True)
    # Bounce and tracking
    scheduled = fields.Datetime(help='Date when the email has been created', default=fields.Datetime.now)
    sent = fields.Datetime(help='Date when the email has been sent')
    exception = fields.Datetime(help='Date of technical error leading to the email not being sent')
    opened = fields.Datetime(help='Date when the email has been opened the first time')
    replied = fields.Datetime(help='Date when this email has been replied for the first time.')
    bounced = fields.Datetime(help='Date when this email has bounced.')
    # Link tracking
    links_click_ids = fields.One2many('link.tracker.click', 'mail_stat_id', string='Links click')
    clicked = fields.Datetime(help='Date when customer clicked on at least one tracked link')
    # Status
    state = fields.Selection(compute="_compute_state",
                             selection=[('outgoing', 'Outgoing'),
                                        ('exception', 'Exception'),
                                        ('sent', 'Sent'),
                                        ('opened', 'Opened'),
                                        ('replied', 'Replied'),
                                        ('bounced', 'Bounced')], store=True)
    state_update = fields.Datetime(compute="_compute_state", string='State Update',
                                    help='Last state update of the mail',
                                    store=True)
    recipient = fields.Char(compute="_compute_recipient")

    @api.depends('sent', 'opened', 'clicked', 'replied', 'bounced', 'exception')
    def _compute_state(self):
        self.update({'state_update': fields.Datetime.now()})
        for stat in self:
            if stat.exception:
                stat.state = 'exception'
            elif stat.sent:
                stat.state = 'sent'
            elif stat.opened or stat.clicked:
                stat.state = 'opened'
            elif stat.replied:
                stat.state = 'replied'
            elif stat.bounced:
                stat.state = 'bounced'
            else:
                stat.state = 'outgoing'

    def _compute_recipient(self):
        for stat in self:
            if stat.model not in self.env:
                continue
            target = self.env[stat.model].browse(stat.res_id)
            if not target or not target.exists():
                continue
            email = ''
            for email_field in ('email', 'email_from'):
                if email_field in target and target[email_field]:
                    email = ' <%s>' % target[email_field]
                    break
            stat.recipient = '%s%s' % (target.display_name, email)

    @api.model
    def create(self, values):
        if 'mail_mail_id' in values:
            values['mail_mail_id_int'] = values['mail_mail_id']
        res = super(MailMailStats, self).create(values)
        return res

    def _get_records(self, mail_mail_ids=None, mail_message_ids=None, domain=None):
        if not self.ids and mail_mail_ids:
            base_domain = [('mail_mail_id_int', 'in', mail_mail_ids)]
        elif not self.ids and mail_message_ids:
            base_domain = [('message_id', 'in', mail_message_ids)]
        else:
            base_domain = [('id', 'in', self.ids)]
        if domain:
            base_domain = ['&'] + domain + base_domain
        return self.search(base_domain)

    def set_opened(self, mail_mail_ids=None, mail_message_ids=None):
        statistics = self._get_records(mail_mail_ids, mail_message_ids, [('opened', '=', False)])
        statistics.write({'opened': fields.Datetime.now()})
        return statistics

    def set_clicked(self, mail_mail_ids=None, mail_message_ids=None):
        statistics = self._get_records(mail_mail_ids, mail_message_ids, [('clicked', '=', False)])
        statistics.write({'clicked': fields.Datetime.now()})
        return statistics

    def set_replied(self, mail_mail_ids=None, mail_message_ids=None):
        statistics = self._get_records(mail_mail_ids, mail_message_ids, [('replied', '=', False)])
        statistics.write({'replied': fields.Datetime.now()})
        return statistics

    def set_bounced(self, mail_mail_ids=None, mail_message_ids=None):
        statistics = self._get_records(mail_mail_ids, mail_message_ids, [('bounced', '=', False)])
        statistics.write({'bounced': fields.Datetime.now()})
        return statistics
