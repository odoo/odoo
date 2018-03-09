# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import threading

from odoo.tools.misc import split_every

from odoo import _, api, fields, models, registry, SUPERUSER_ID
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    """ Update partner to add a field about notification preferences. Add a generic opt-out field that can be used
       to restrict usage of automatic email templates. """
    _name = "res.partner"
    _inherit = ['res.partner', 'mail.thread', 'mail.activity.mixin']
    _mail_flat_thread = False

    message_bounce = fields.Integer('Bounce', help="Counter of the number of bounced emails for this contact", default=0)
    opt_out = fields.Boolean(
        'Opt-Out', help="If opt-out is checked, this contact has refused to receive emails for mass mailing and marketing campaign. "
                        "Filter 'Available for Mass Mailing' allows users to filter the partners when performing mass mailing.")
    channel_ids = fields.Many2many('mail.channel', 'mail_channel_partner', 'partner_id', 'channel_id', string='Channels', copy=False)

    @api.multi
    def message_get_suggested_recipients(self):
        recipients = super(Partner, self).message_get_suggested_recipients()
        for partner in self:
            partner._message_add_suggested_recipient(recipients, partner=partner, reason=_('Partner Profile'))
        return recipients

    @api.multi
    def message_get_default_recipients(self):
        return dict((res_id, {'partner_ids': [res_id], 'email_to': False, 'email_cc': False}) for res_id in self.ids)

    @api.model
    def _notify_prepare_template_context(self, message, record, notif_values):
        company, user, signature = False, False, ''

        # compute author and company
        if record and hasattr(record, 'company_id'):
            company = record.company_id
        if message.author_id and message.author_id.user_ids:
            user = message.author_id.user_ids[0]
            if notif_values.pop('add_sign', True):
                signature = user.signature
        else:
            user = self.env.user
        if not company:
            company = user.company_id

        if company.website:
            website_url = 'http://%s' % company.website if not company.website.lower().startswith(('http:', 'https:')) else company.website
        else:
            website_url = False

        model_name = False
        if message.model:
            model_name = self.env['ir.model']._get(message.model).display_name

        tracking = []
        for tracking_value in self.env['mail.tracking.value'].sudo().search([('mail_message_id', '=', message.id)]):
            tracking.append((tracking_value.field_desc,
                             tracking_value.get_old_display_value()[0],
                             tracking_value.get_new_display_value()[0]))

        is_discussion = message.subtype_id.id == self.env['ir.model.data'].xmlid_to_res_id('mail.mt_comment')

        return {
            'message': message,
            'signature': signature,
            'website_url': website_url,
            'company': company,
            'model_name': model_name,
            'record': record,
            'tracking_values': tracking,
            'is_discussion': is_discussion,
            'subtype': message.subtype_id,
        }

    @api.model
    def _notify_udpate_notifications(self, message, record, recipient_data):
        for r in recipient_data:
            if r[1] == 'email':
                self.env['mail.notification'].sudo().create({
                    'mail_message_id': message.id,
                    'res_partner_id': r[0],
                    'is_email': True,
                    'is_read': True,  # handle by email discards Inbox notification
                    'email_status': 'ready',
                })
            else:
                self.env['mail.notification'].sudo().create({
                    'mail_message_id': message.id,
                    'res_partner_id': r[0],
                    'is_email': False,
                    'is_read': False,
                })

    @api.model
    def _notify(self, message, record, recipient_data, layout=False, force_send=False, send_after_commit=True, values=None):
        """ Notify partners of a message either by email either by Inbox and by chat.

        :param recipient_data: list of (pid, DD, FF, GG)
        :param layout: xml_id of layout to use to encapusulate notification emails
        :param force_send: send notification emails now or use the email scheduler
        :param send_after_commit: if force_send, send emails after the tx end instead of during the tx
        :param dict values: values used to compute the notification process, containing

         * add_sign: add user signature to notification email, default is True
         * mail_auto_delete: auto delete send emails, default is True
         * other values are given to the context used to render the notification template, allowing customization

        """
        if not recipient_data:
            return True
        values = values if values is not None else {}

        email_rdata = [d for d in recipient_data if d[1] == 'email']
        inbox_rdata = [d for d in recipient_data if d[1] == 'inbox']

        template_xmlid = layout if layout else 'mail.message_notification_email'
        try:
            base_template = self.env.ref(template_xmlid, raise_if_not_found=True)
        except ValueError:
            _logger.warning('QWeb template %s not found when sending notification emails. Skipping.' % (template_xmlid))
            return False

        render_values = self._notify_prepare_template_context(message, record, values)

        # prepare notification mail values
        base_mail_values = {
            'mail_message_id': message.id,
            'mail_server_id': message.mail_server_id.id,
            'auto_delete': values.pop('mail_auto_delete', True),
            'references': message.parent_id.message_id if message.parent_id else False,
        }
        if record and hasattr(record, '_notify_specific_email_values'):
            custom_values = record._notify_specific_email_values(message)
            base_mail_values.update(custom_values)

        # classify recipients: actions / no action
        if record and hasattr(record, '_notify_classify_recipients'):
            recipients = record._notify_classify_recipients( email_rdata)
        else:
            recipients = self.env['mail.thread']._notify_classify_recipients(email_rdata)

        emails, MailSudo = self.env['mail.mail'].sudo(), self.env['mail.mail'].sudo()
        for rvals in recipients.values():
            template_values = {**render_values, **rvals, **values}  # fixme: set button_unfollow to none
            # 'subject': message.subject or (message.record_name and 'Re: %s' % message.record_name),
            body = base_template.render(template_values, engine='ir.qweb'),
            body = self.env['mail.thread']._replace_local_links(body)
            # send email
            mail_mail_values = {'body_html': body}
            mail_mail_values.update(base_mail_values)
            # new_emails = self._notify_send(message, record, body, rvals['recipients'], **base_mail_values)

            for email_chunk in split_every(50, rvals['recipients']):
                if record and hasattr(record, '_notify_email_recipients'):
                    recipient_values = record._notify_email_recipients(message, email_chunk)
                else:
                    recipient_values = self.env['mail.thread']._notify_email_recipients(message, email_chunk)
                mail_mail_values.update(recipient_values)
                emails |= MailSudo.create(mail_mail_values)

        # update notifications - ZIZISSE TEMPORARY
        if record and hasattr(record, '_notify_create_notifications'):
            record._notify_create_notifications(message, recipient_data)
        else:
            self._notify_udpate_notifications(message, record, recipient_data)

        # NOTE:
        #   1. for more than 50 followers, use the queue system
        #   2. do not send emails immediately if the registry is not loaded,
        #      to prevent sending email during a simple update of the database
        #      using the command-line.
        MAX_RECIPIENTS = 50
        test_mode = getattr(threading.currentThread(), 'testing', False)
        if force_send and len(emails) < MAX_RECIPIENTS and \
                (not self.pool._init or test_mode):
            email_ids = emails.ids
            dbname = self.env.cr.dbname
            _context = self._context

            def send_notifications():
                db_registry = registry(dbname)
                with api.Environment.manage(), db_registry.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, _context)
                    env['mail.mail'].browse(email_ids).send()

            # unless asked specifically, send emails after the transaction to
            # avoid side effects due to emails being sent while the transaction fails
            if not test_mode and send_after_commit:
                self._cr.after('commit', send_notifications)
            else:
                emails.send()

        if inbox_rdata:
            self._notify_by_chat(message, inbox_rdata)

        return True

    @api.model
    def _notify_by_chat(self, message, recipient_data):
        """ Broadcast the message to all the partner since """
        message_values = message.message_format()[0]
        notifications = []
        for partner_data in recipient_data:
            notifications.append([(self._cr.dbname, 'ir.needaction', partner_data[0]), dict(message_values)])
        self.env['bus.bus'].sendmany(notifications)

    @api.model
    def get_needaction_count(self):
        """ compute the number of needaction of the current user """
        if self.env.user.partner_id:
            self.env.cr.execute("""
                SELECT count(*) as needaction_count
                FROM mail_message_res_partner_needaction_rel R
                WHERE R.res_partner_id = %s AND (R.is_read = false OR R.is_read IS NULL)""", (self.env.user.partner_id.id,))
            return self.env.cr.dictfetchall()[0].get('needaction_count')
        _logger.error('Call to needaction_count without partner_id')
        return 0

    @api.model
    def get_starred_count(self):
        """ compute the number of starred of the current user """
        if self.env.user.partner_id:
            self.env.cr.execute("""
                SELECT count(*) as starred_count
                FROM mail_message_res_partner_starred_rel R
                WHERE R.res_partner_id = %s """, (self.env.user.partner_id.id,))
            return self.env.cr.dictfetchall()[0].get('starred_count')
        _logger.error('Call to starred_count without partner_id')
        return 0

    @api.model
    def get_static_mention_suggestions(self):
        """ To be overwritten to return the id, name and email of partners used as static mention
            suggestions loaded once at webclient initialization and stored client side. """
        return []

    @api.model
    def get_mention_suggestions(self, search, limit=8):
        """ Return 'limit'-first partners' id, name and email such that the name or email matches a
            'search' string. Prioritize users, and then extend the research to all partners. """
        search_dom = expression.OR([[('name', 'ilike', search)], [('email', 'ilike', search)]])
        fields = ['id', 'name', 'email']

        # Search users
        domain = expression.AND([[('user_ids.id', '!=', False)], search_dom])
        users = self.search_read(domain, fields, limit=limit)

        # Search partners if less than 'limit' users found
        partners = []
        if len(users) < limit:
            partners = self.search_read(search_dom, fields, limit=limit)
            # Remove duplicates
            partners = [p for p in partners if not len([u for u in users if u['id'] == p['id']])] 

        return [users, partners]
