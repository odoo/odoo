# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, tools

_logger = logging.getLogger(__name__)


class FetchmailMail(models.Model):
    _name = 'fetchmail.mail'
    _description = 'Inbox Mail'
    _order = 'date desc, id desc'
    _rec_name = 'subject'

    fetchmail_server_id = fields.Many2one('fetchmail.server', 'Mail Server', index=True, ondelete='cascade')

    # Email headers
    email_from = fields.Char('From')
    email_to = fields.Char('To')
    email_cc = fields.Char('CC')
    email_bcc = fields.Char('BCC')

    # Partner resolution (no force_create: only link to existing partners)
    author_id = fields.Many2one(
        'res.partner', 'Author',
        compute='_compute_author_id', store=True,
    )
    partner_to = fields.Many2many(
        'res.partner', 'fm_mail_partner_to_rel', 'mail_id', 'partner_id',
        string='To', compute='_compute_partner_to',
    )
    partner_cc = fields.Many2many(
        'res.partner', 'fm_mail_partner_cc_rel', 'mail_id', 'partner_id',
        string='CC', compute='_compute_partner_cc',
    )
    partner_bcc = fields.Many2many(
        'res.partner', 'fm_mail_partner_bcc_rel', 'mail_id', 'partner_id',
        string='BCC', compute='_compute_partner_bcc',
    )

    subject = fields.Char('Subject')
    body = fields.Html('Body', sanitize=True)
    date = fields.Datetime('Date', index=True)
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'fetchmail_mail_attachment_rel', 'mail_id', 'attachment_id',
        string='Attachments',
    )
    tag_ids = fields.Many2many(
        'fetchmail.tag',
        'fetchmail_mail_tag_rel', 'mail_id', 'tag_id',
        string='Tags',
    )
    preview = fields.Char('Preview', compute='_compute_preview', store=True)

    # Threading
    parent_id = fields.Many2one('fetchmail.mail', 'Parent Mail', index=True, ondelete='set null')
    child_ids = fields.One2many('fetchmail.mail', 'parent_id', 'Replies')

    # State
    is_starred = fields.Boolean('Starred', index=True)
    mail_type = fields.Selection([
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing'),
    ], required=True, default='incoming', index=True)
    mail_status = fields.Selection([
        ('new', 'New'),
        ('open', 'Open'),
        ('read', 'Read'),
        ('draft', 'Draft'),
        ('outgoing', 'Outgoing'),
        ('sent', 'Sent'),
        ('error', 'Error'),
        ('cancel', 'Cancelled'),
    ], required=True, default='new', index=True)

    # Linked record (optional)
    mail_message_id = fields.Many2one('mail.message', 'Linked Message', index=True, ondelete='set null')
    model = fields.Char('Related Model')
    res_id = fields.Integer('Related Record ID')

    @api.depends('email_from')
    def _compute_author_id(self):
        for mail in self:
            if not mail.email_from:
                mail.author_id = False
                continue
            partners = self.env['mail.thread']._mail_find_partner_from_emails(
                [mail.email_from], force_create=False,
            )
            mail.author_id = partners[0] if partners else False

    @api.depends('email_to')
    def _compute_partner_to(self):
        for mail in self:
            mail.partner_to = mail._partners_from_email_str(mail.email_to)

    @api.depends('email_cc')
    def _compute_partner_cc(self):
        for mail in self:
            mail.partner_cc = mail._partners_from_email_str(mail.email_cc)

    @api.depends('email_bcc')
    def _compute_partner_bcc(self):
        for mail in self:
            mail.partner_bcc = mail._partners_from_email_str(mail.email_bcc)

    def _partners_from_email_str(self, email_str):
        emails = tools.email_split(email_str or '')
        if not emails:
            return self.env['res.partner']
        partners = self.env['mail.thread']._mail_find_partner_from_emails(emails, force_create=False)
        return self.env['res.partner'].browse([p.id for p in partners if p.id])

    @api.depends('body')
    def _compute_preview(self):
        for mail in self:
            plain = (tools.html2plaintext(mail.body or '') or '').strip()
            mail.preview = plain[:150]

    def _store_fetchmail_mail_fields(self, fields_list):
        fields_list.attr('subject')
        fields_list.attr('email_from')
        fields_list.attr('preview')
        fields_list.attr('date')
        fields_list.attr('mail_status')
        fields_list.attr('mail_type')
        fields_list.attr('is_starred')
        fields_list.attr('model')
        fields_list.attr('res_id')
