# -*- coding: utf-8 -*-
import logging
from odoo import models, api, _
from lxml.builder import E
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _get_default_activity_view(self):
        """ Generates an empty activity view.

        :returns: a activity view as an lxml document
        :rtype: etree._Element
        """
        field = E.field(name=self._rec_name_fallback())
        activity_box = E.div(field, {'t-name': "activity-box"})
        templates = E.templates(activity_box)
        return E.activity(templates, string=self._description)

    def _notify_email_headers(self):
        """
            Generate the email headers based on record
        """
        if not self:
            return {}
        self.ensure_one()
        return repr(self._notify_email_header_dict())

    def _notify_email_header_dict(self):
        return {
            'X-Odoo-Objects': "%s-%s" % (self._name, self.id),
        }

    @api.model
    def _notify_admins(self, subject, body, helper={}, **kwargs):
        """
            Posts notifications about system failures on Admins channel (recreates the channel if it no longer exists).
        """
        ir_model_data = self.env['ir.model.data']
        model_mail_channel = self.env['mail.channel']
        odoobot_id = ir_model_data.xmlid_to_res_id("base.partner_root")
        admins_channel = ir_model_data.xmlid_to_object('mail.channel_admins')
        # Create a new channel if it no longer exists
        if not admins_channel:
            admins_channel = model_mail_channel.sudo().with_context(mail_create_nosubscribe=True).create({
                'group_ids': [(4, self.env.ref('base.group_system').id)],
                'group_public_id': self.env.ref('base.group_system').id,
                'public': 'groups',
                'channel_type': 'channel',
                'email_send': False,
                'name': 'Administrators',
                'description': _('Channel to post notifications about system silent failures to make admins aware of them.')
            })
        # Get the message to post (body) from template
        helper_related_doc = helper.get("related_doc", False)
        helper_related_view_url = helper.get("related_view_url", False)
        helper_related_view_text = helper.get("related_view_text", False)
        message = self._format_notification(subject, body, helper_related_doc, helper_related_view_url, helper_related_view_text)
        # Check Repeat delay (default : 7 days -> can be updated in method parameters)
        channel_last_message = self.env['mail.message'].search([
            ("channel_ids", "in", [admins_channel.id]),
            ("subject", "=", subject)], limit=1)
        message_after_repeat_delay = False
        if channel_last_message:
            repeat_delay = kwargs.get('repeat_delay', None) or timedelta(days=7)
            repeat_last_datetime = datetime.now() - repeat_delay
            message_after_repeat_delay = channel_last_message.date < repeat_last_datetime
        if not channel_last_message or message_after_repeat_delay:
            admins_channel.sudo().message_post(subject=subject, body=message, author_id=odoobot_id, message_type="comment", subtype_xmlid="mail.mt_comment")

    @api.model
    def _format_record_link(self, name):
        """
            Get record local url (used to get links to targeted records in notifications : mail servers with failures...).
        """
        return {
            "url": "/mail/view?model=%s&res_id=%s" % (self._name, self.id),
            "text": name,
        }

    @api.model
    def _format_notification(self, subject, message, helper_related_doc, helper_related_view_url, helper_related_view_text):
        """
            Returns the notification message to post on admins channel using a template.
            If template not found > returns the original message.
        """
        render_context = {
            "subject": subject,
            "message": message,
            "helper_related_doc": helper_related_doc,
            "helper_related_view_url": helper_related_view_url,
            "helper_related_view_text": helper_related_view_text,
        }
        template = self.env.ref('mail.mail_channel_notify_admins', raise_if_not_found=False)
        if not template:
            _logger.warning('Template "mail.mail_channel_notify_admins" was not found. Cannot send Admins notifications.')
            return message
        notification_body = template._render(render_context, engine='ir.qweb', minimal_qcontext=True)
        # Local > global links
        notification_body = self.env['mail.render.mixin']._replace_local_links(notification_body)
        return notification_body

    @api.model
    def _get_admin_notification(self, failure_type, module_messages=None):
        """
            To simplify failure notification process, this method will work as wrapper and will
            return parameters (messages + doc links) to use in '_notify_admins' depending on a 'failure_type' value,
            which makes code easier to extend if other failure messages added.
            * 'failure_type' strings follow the structure : [MODULE_NAME__TARGET_FAILURE]

            Failure messages can be added/overrided in other modules using 'module_messages' param.
        """
        messages = {
            "mail__smtp_connection": lambda failed_emails_counter, mail_sms_notifications_window_action: (
                _('Odoo has been unable to send email(s)'),
                _(
                    "%(failed_emails_counter)d email(s) could not be sent due to technical issues.\n"
                    "To solve SMTP connection related issues make sure that SMTP configuration is correct and click on 'Test Connection'.\n"
                    "If your configuration is incorrect, an error message should help you diagnose the issue.\n"
                    "Ex : If you get a '[AUTHENTICATIONFAILED] Invalid credentials (Failure)' warning when you test connection on a Gmail address, "
                    "activate the Less secure app access option.\n"
                    "In addition to that, enable the IMAP setting on your Gmail account.\n"
                    "You can check your mail notifications for more details about failed emails "
                    "(an error message should help you diagnose the issue.)"
                ) % {
                    'failed_emails_counter': failed_emails_counter,
                },
                {
                   "related_doc": 'https://www.odoo.com/documentation/user/online/discuss/email_servers.html',
                   "related_view_url": "/web#action=%(mail_sms_notifications_window_action)s&amp;view_type=list" % {
                       'mail_sms_notifications_window_action': mail_sms_notifications_window_action
                   },
                   "related_view_text": "go to mail notifications"
                }
            ),

            "mail__invalid_recipient": lambda failed_ignored_emails_counter, mail_sms_notifications_window_action: (
                _('failed emails due to invalid email address'),
                _(
                    "%(failed_ignored_emails_counter)d email(s) failed / ignored to avoid blocking delivery to other recipients.\n"
                    "Please make sure that recipient's email address really exists and if it's actually valid.\n"
                    "You can check your mail notifications for more details about failed emails "
                    "(an error message should help you diagnose the issue.)"
                ) % {
                    'failed_ignored_emails_counter': failed_ignored_emails_counter,
                },
                {
                   "related_view_url": "/web#action=%(mail_sms_notifications_window_action)s&amp;view_type=list" % {
                       'mail_sms_notifications_window_action': mail_sms_notifications_window_action
                   },
                   "related_view_text": "go to mail notifications"
                }
            ),

            "iap__low_credits": lambda account_credits: (
                _('Your credits balance is too low'),
                _(
                    "Your current balance reached %(account_credits)1.2f, It’s time to recharge your credits!\n"
                    "To avoid service interruption (SMS, snailmail, lead enrichment...),"
                    "please go to your 'IAP Portal' [Settings app > Odoo IAP > View my Services].\n"
                    "From there, you can view your current balance, recharge your credits, "
                    "review your consumption and set another reminder (by email) to when credits are low."
                ) % {
                    'account_credits': account_credits
                },
                {
                   "related_doc": 'https://www.odoo.com/documentation/user/online/general/in_app_purchase/in_app_purchase.html'
                }
            ),

            "base__cron": lambda record_link, cron_exception, cron_error_datetime, cron_database: (
                _('Scheduled action failure'),
                _(
                    "An error occurred while running a cron job in Odoo.\n\n"
                    "Failure details :\n"
                    "- Execption: %(cron_exception)s\n"
                    "- Occurred on: %(cron_error_datetime)s\n"
                    "- Database: %(cron_database)s"
                ) % {
                    'cron_exception': cron_exception,
                    'cron_error_datetime': cron_error_datetime,
                    'cron_database': cron_database
                },
                {
                    "related_view_url": record_link.get('url', False),
                    "related_view_text": record_link.get('text', False),
                }
            )
        }
        # This way we can add messages in other models or even override genesis ones
        if module_messages:
            messages.update(module_messages)
        return messages[failure_type]
