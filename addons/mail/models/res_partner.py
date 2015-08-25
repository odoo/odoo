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

    @api.multi
    def _notify(self, message, force_send=False, user_signature=True):
        email_recipients = self.get_partners_to_email(message, self)
        return email_recipients._notify_email(message, force_send=force_send, user_signature=user_signature)

    def get_partners_to_email(self, message, recipients):
        """ Return the list of partners to notify, based on their preferences.

            :param browse_record message: mail.message to notify
            :param record set recipients: recipients
        """
        email_recipients = self.env['res.partner']
        for partner in recipients:
            # Do not send to partners without email address defined
            if not partner.email:
                continue
            # Do not send to partners having same email address than the author (can cause loops or bounce effect due to messy database)
            if message.author_id and message.author_id.email == partner.email:
                continue
            # Partner does not want to receive any emails or is opt-out
            if partner.notify_email == 'none':
                continue
            email_recipients |= partner
        return email_recipients

    @api.model
    def get_signature_footer(self, user_id, res_model=None, res_id=None, user_signature=True):
        """ Format a standard footer for notification emails (such as pushed messages
            notification or invite emails).
            Format:
                <p>--<br />
                    Administrator
                </p>
                <div>
                    <small>Sent from <a ...>Your Company</a> using <a ...>Odoo</a>.</small>
                </div>
        """
        footer = ""
        if not user_id:
            return footer

        # add user signature
        user = self.env.user
        if user_signature:
            if self.env.user.signature:
                signature = user.signature
            else:
                signature = "--<br />%s" % user.name
            footer = tools.append_content_to_html(footer, signature, plaintext=False)

        # add company signature
        if user.company_id.website:
            website_url = ('http://%s' % user.company_id.website) if not user.company_id.website.lower().startswith(('http:', 'https:')) \
                else user.company_id.website
            company = "<a style='color:inherit' href='%s'>%s</a>" % (website_url, user.company_id.name)
        else:
            company = user.company_id.name
        sent_by = _('Sent by %(company)s using %(odoo)s')

        signature_company = '<br /><small>%s</small>' % (sent_by % {
            'company': company,
            'odoo': "<a style='color:inherit' href='https://www.odoo.com/'>Odoo</a>"
        })
        footer = tools.append_content_to_html(footer, signature_company, plaintext=False, container_tag='div')

        return footer

    @api.multi
    def _notify_email(self, message, force_send=False, user_signature=True):
        # compute partners
        if not self.ids:
            return True
        email_pids = self.ids
        # rebrowse as sudo to avoid access rigths on author, user, ... -> portal / public goes through this method
        message_sudo = message.sudo()

        # compute email body (signature, company data)
        body_html = message_sudo.body
        # add user signature except for mail.channels, where users are usually adding their own signatures already
        user_id = message_sudo.author_id and message_sudo.author_id.user_ids and message_sudo.author_id.user_ids[0] and message_sudo.author_id.user_ids[0].id or None
        signature_company = self.get_signature_footer(user_id, res_model=message_sudo.model, res_id=message_sudo.res_id, user_signature=(user_signature and message_sudo.model != 'mail.channel'))
        if signature_company:
            body_html = tools.append_content_to_html(body_html, signature_company, plaintext=False, container_tag='div')

        # compute email references
        references = message_sudo.parent_id.message_id if message_sudo.parent_id else False

        # custom values
        custom_values = dict()
        if message_sudo.model and message_sudo.res_id and self.pool.get(message_sudo.model) and hasattr(self.pool[message_sudo.model], 'message_get_email_values'):
            custom_values = self.env[message_sudo.model].browse(message_sudo.res_id).message_get_email_values(message_sudo)

        # create email values
        max_recipients = 50
        chunks = [email_pids[x:x + max_recipients] for x in xrange(0, len(email_pids), max_recipients)]
        emails = self.env['mail.mail']
        for chunk in chunks:
            mail_values = {
                'mail_message_id': message_sudo.id,
                'auto_delete': self._context.get('mail_auto_delete', True),
                'mail_server_id': self._context.get('mail_server_id', False),
                'body_html': body_html,
                'recipient_ids': [(4, id) for id in chunk],
                'references': references,
            }
            mail_values.update(custom_values)
            emails |= self.env['mail.mail'].create(mail_values)
        # NOTE:
        #   1. for more than 50 followers, use the queue system
        #   2. do not send emails immediately if the registry is not loaded,
        #      to prevent sending email during a simple update of the database
        #      using the command-line.
        if force_send and len(chunks) < 2 and \
               (not self.pool._init or
                getattr(threading.currentThread(), 'testing', False)):
            emails.send()
        return True
