# -*- coding: utf-8 -*-

from openerp import _, api, fields, models


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

    @api.multi
    def message_get_suggested_recipients(self):
        recipients = super(Partner, self).message_get_suggested_recipients()
        for partner in self:
            partner._message_add_suggested_recipient(recipients, partner=partner, reason=_('Partner Profile'))
        return recipients

    @api.multi
    def message_get_default_recipients(self):
        return dict((res_id, {'partner_ids': [res_id], 'email_to': False, 'email_cc': False}) for res_id in self.ids)
