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
    def _notify_prepare_template_context(self, message):
        # compute signature
        signature = ""
        if message.author_id and message.author_id.user_ids and message.author_id.user_ids[0].signature:
            signature = message.author_id.user_ids[0].signature
        elif message.author_id:
            signature = "<p>-- <br/>%s</p>" % message.author_id.name

        # compute Sent by
        if message.author_id and message.author_id.user_ids:
            user = message.author_id.user_ids[0]
        else:
            user = self.env.user
        if user.company_id.website:
            website_url = 'http://%s' % user.company_id.website if not user.company_id.website.lower().startswith(('http:', 'https:')) else user.company_id.website
        else:
            website_url = False

        model_name = False
        if message.model:
            model_name = self.env['ir.model']._get(message.model).display_name

        record_name = message.record_name

        tracking = []
        for tracking_value in self.env['mail.tracking.value'].sudo().search([('mail_message_id', '=', message.id)]):
            tracking.append((tracking_value.field_desc,
                             tracking_value.get_old_display_value()[0],
                             tracking_value.get_new_display_value()[0]))

        is_discussion = message.subtype_id.id == self.env['ir.model.data'].xmlid_to_res_id('mail.mt_comment')

        record = False
        if message.res_id and message.model in self.env:
            record = self.env[message.model].browse(message.res_id)

        company = user.company_id;
        if record and hasattr(record, 'company_id'):
            company = record.company_id;
        company_name = company.name;

        return {
            'signature': signature,
            'website_url': website_url,
            'company': company,
            'company_name': company_name,
            'model_name': model_name,
            'record': record,
            'record_name': record_name,
            'tracking': tracking,
            'is_discussion': is_discussion,
            'subtype': message.subtype_id,
        }

    @api.model
    def _notify_prepare_email_values(self, message):
        # compute email references
        references = message.parent_id.message_id if message.parent_id else False

        # custom values
        custom_values = dict()
        if message.res_id and message.model in self.env and hasattr(self.env[message.model], 'message_get_email_values'):
            custom_values = self.env[message.model].browse(message.res_id).message_get_email_values(message)

        mail_values = {
            'mail_message_id': message.id,
            'mail_server_id': message.mail_server_id.id,
            'auto_delete': self._context.get('mail_auto_delete', True),
            'references': references,
        }
        mail_values.update(custom_values)
        return mail_values

    @api.model
    def _notify_send(self, body, subject, recipients, **mail_values):
        emails = self.env['mail.mail']
        recipients_nbr = len(recipients)
        for email_chunk in split_every(50, recipients.ids):
            # TDE FIXME: missing message parameter. So we will find mail_message_id
            # in the mail_values and browse it. It should already be in the
            # cache so should not impact performances.
            mail_message_id = mail_values.get('mail_message_id')
            message = self.env['mail.message'].browse(mail_message_id) if mail_message_id else None
            if message and message.model and message.res_id and message.model in self.env and hasattr(self.env[message.model], 'message_get_recipient_values'):
                tig = self.env[message.model].browse(message.res_id)
                recipient_values = tig.message_get_recipient_values(notif_message=message, recipient_ids=email_chunk)
            else:
                recipient_values = self.env['mail.thread'].message_get_recipient_values(notif_message=None, recipient_ids=email_chunk)
            create_values = {
                'body_html': body,
                'subject': subject,
            }
            create_values.update(mail_values)
            create_values.update(recipient_values)
            emails |= self.env['mail.mail'].create(create_values)
        return emails, recipients_nbr

    @api.model
    def _notify_udpate_notifications(self, emails):
        for email in emails:
            notifications = self.env['mail.notification'].sudo().search([
                ('mail_message_id', '=', email.mail_message_id.id),
                ('res_partner_id', 'in', email.recipient_ids.ids)])
            notifications.write({
                'is_email': True,
                'is_read': True,  # handle by email discards Inbox notification
                'email_status': 'ready',
            })

    @api.multi
    def _notify(self, message, force_send=False, send_after_commit=True, user_signature=True):
        """ Method to send email linked to notified messages. The recipients are
        the recordset on which this method is called.

        :param boolean force_send: send notification emails now instead of letting the scheduler handle the email queue
        :param boolean send_after_commit: send notification emails after the transaction end instead of durign the
                                          transaction; this option is used only if force_send is True
        :param user_signature: add current user signature to notification emails """
        if not self.ids:
            return True

        # existing custom notification email
        base_template = None
        if message.model and self._context.get('custom_layout', False):
            base_template = self.env.ref(self._context['custom_layout'], raise_if_not_found=False)
        if not base_template:
            base_template = self.env.ref('mail.mail_template_data_notification_email_default')

        base_template_ctx = self._notify_prepare_template_context(message)
        if not user_signature:
            base_template_ctx['signature'] = False
        base_mail_values = self._notify_prepare_email_values(message)

        # classify recipients: actions / no action
        if message.model and message.res_id and hasattr(self.env[message.model], '_message_notification_recipients'):
            recipients = self.env[message.model].browse(message.res_id)._message_notification_recipients(message, self)
        else:
            recipients = self.env['mail.thread']._message_notification_recipients(message, self)

        emails = self.env['mail.mail']
        recipients_nbr, recipients_max = 0, 50
        for email_type, recipient_template_values in recipients.items():
            if recipient_template_values['followers']:
                # generate notification email content
                template_fol_values = dict(base_template_ctx, **recipient_template_values)  # fixme: set button_unfollow to none
                template_fol_values['has_button_follow'] = False
                template_fol = base_template.with_context(**template_fol_values)
                # generate templates for followers and not followers
                fol_values = template_fol.generate_email(message.id, fields=['body_html', 'subject'])
                # send email
                new_emails, new_recipients_nbr = self._notify_send(fol_values['body'], fol_values['subject'], recipient_template_values['followers'], **base_mail_values)
                # update notifications
                self._notify_udpate_notifications(new_emails)

                emails |= new_emails
                recipients_nbr += new_recipients_nbr
            if recipient_template_values['not_followers']:
                # generate notification email content
                template_not_values = dict(base_template_ctx, **recipient_template_values)  # fixme: set button_follow to none
                template_not_values['has_button_unfollow'] = False
                template_not = base_template.with_context(**template_not_values)
                # generate templates for followers and not followers
                not_values = template_not.generate_email(message.id, fields=['body_html', 'subject'])
                # send email
                new_emails, new_recipients_nbr = self._notify_send(not_values['body'], not_values['subject'], recipient_template_values['not_followers'], **base_mail_values)
                # update notifications
                self._notify_udpate_notifications(new_emails)

                emails |= new_emails
                recipients_nbr += new_recipients_nbr

        # NOTE:
        #   1. for more than 50 followers, use the queue system
        #   2. do not send emails immediately if the registry is not loaded,
        #      to prevent sending email during a simple update of the database
        #      using the command-line.
        test_mode = getattr(threading.currentThread(), 'testing', False)
        if force_send and recipients_nbr < recipients_max and \
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

        return True

    @api.multi
    def _notify_by_chat(self, message):
        """ Broadcast the message to all the partner since """
        message_values = message.message_format()[0]
        notifications = []
        for partner in self:
            notifications.append([(self._cr.dbname, 'ir.needaction', partner.id), dict(message_values)])
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
