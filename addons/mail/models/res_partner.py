# -*- coding: utf-8 -*-

import threading

from openerp import _, api, fields, models, tools


class Partner(models.Model):
    """ Update partner to add a field about notification preferences. Add a generic opt-out field that can be used
       to restrict usage of automatic email templates. """
    _name = "res.partner"
    _inherit = ['res.partner', 'mail.thread']
    _mail_flat_thread = False
    _mail_mass_mailing = _('Customers')

    notify_email = fields.Selection([
        ('none', 'Never'),
        ('always', 'All Messages')],
        'Email Messages and Notifications', required=True,
        oldname='notification_email_send', default='always',
        help="Policy to receive emails for new messages pushed to your personal Inbox:\n"
             "- Never: no emails are sent\n"
             "- All Messages: for every notification you receive in your Inbox")
    opt_out = fields.Boolean(
        'Opt-Out', help="If opt-out is checked, this contact has refused to receive emails for mass mailing and marketing campaign. "
                        "Filter 'Available for Mass Mailing' allows users to filter the partners when performing mass mailing.")
    channel_ids = fields.Many2many('mail.channel', 'mail_channel_partner', 'partner_id', 'channel_id', string='Channels')

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
            signature = "<p>--<br />%s</p>" % message.author_id.name

        # compute Sent by
        if message.author_id and message.author_id.user_ids:
            user = message.author_id.user_ids[0]
        else:
            user = self.env.user
        if user.company_id.website:
            website_url = 'http://%s' % user.company_id.website if not user.company_id.website.lower().startswith(('http:', 'https:')) else user.company_id.website
        else:
            website_url = False
        company_name = user.company_id.name

        model_name = False
        if message.model:
            model_name = self.env['ir.model'].sudo().search([('model', '=', self.env[message.model]._name)]).name_get()[0][1]

        record_name = message.record_name

        tracking = []
        for tracking_value in message.tracking_value_ids:
            tracking.append((tracking_value.field_desc,
                             tracking_value.get_old_display_value()[0],
                             tracking_value.get_new_display_value()[0]))

        return {
            'signature': signature,
            'website_url': website_url,
            'company_name': company_name,
            'model_name': model_name,
            'record_name': record_name,
            'tracking': tracking,
        }

    @api.model
    def _notify_prepare_email_values(self, message):
        # compute email references
        references = message.parent_id.message_id if message.parent_id else False

        # custom values
        custom_values = dict()
        if message.model and message.res_id and self.pool.get(message.model) and hasattr(self.pool[message.model], 'message_get_email_values'):
            custom_values = self.env[message.model].browse(message.res_id).message_get_email_values(message)

        mail_values = {
            'mail_message_id': message.id,
            'auto_delete': self._context.get('mail_auto_delete', True),
            'references': references,
        }
        mail_values.update(custom_values)
        return mail_values

    @api.model
    def _notify_send(self, body, subject, recipients, **mail_values):
        emails = self.env['mail.mail']
        recipients_nbr, recipients_max = 0, 50
        email_chunks = [recipients[x:x + recipients_max] for x in xrange(0, len(recipients), recipients_max)]
        for email_chunk in email_chunks:
            create_values = {
                'body_html': body,
                'subject': subject,
                'recipient_ids': [(4, recipient.id) for recipient in email_chunk],
            }
            create_values.update(mail_values)
            emails |= self.env['mail.mail'].create(create_values)
        return emails, recipients_nbr

    @api.multi
    def _notify(self, message, force_send=False, user_signature=True):
        """ Method to send email linked to notified messages. The recipients are
        the recordset on which this method is called. """
        if not self.ids:
            return True

        # existing custom notification email
        if message.model:
            base_template = self.env.ref('mail.mail_template_data_notification_email_%s' % message.model.replace('.', '_'), raise_if_not_found=False)
            if base_template:
                # do something custom
                pass
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
        for email_type, recipient_template_values in recipients.iteritems():
            if recipient_template_values['followers']:
                # generate notification email content
                template_fol_values = dict(base_template_ctx, **recipient_template_values)  # fixme: set button_unfollow to none
                template_fol_values['button_follow'] = False
                template_fol = base_template.with_context(**template_fol_values)
                # generate templates for followers and not followers
                fol_values = template_fol.generate_email(message.id, fields=['body_html', 'subject'])
                # send email
                new_emails, new_recipients_nbr = self._notify_send(fol_values['body'], fol_values['subject'], recipient_template_values['followers'], **base_mail_values)
                emails |= new_emails
                recipients_nbr += new_recipients_nbr
            if recipient_template_values['not_followers']:
                # generate notification email content
                template_not_values = dict(base_template_ctx, **recipient_template_values)  # fixme: set button_follow to none
                template_not_values['button_unfollow'] = False
                template_not = base_template.with_context(**template_not_values)
                # generate templates for followers and not followers
                not_values = template_not.generate_email(message.id, fields=['body_html', 'subject'])
                # send email
                new_emails, new_recipients_nbr = self._notify_send(not_values['body'], not_values['subject'], recipient_template_values['not_followers'], **base_mail_values)
                emails |= new_emails
                recipients_nbr += new_recipients_nbr

        # NOTE:
        #   1. for more than 50 followers, use the queue system
        #   2. do not send emails immediately if the registry is not loaded,
        #      to prevent sending email during a simple update of the database
        #      using the command-line.
        if force_send and recipients_nbr < recipients_max and \
                (not self.pool._init or getattr(threading.currentThread(), 'testing', False)):
            emails.send()

        return True
