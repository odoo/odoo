from odoo import fields, models, _
from odoo.tools.mail import parse_contact_from_email


class MailTestTLead(models.Model):
    """ Lead-like model for business flows testing """
    _name = "mail.test.lead"
    _description = 'Lead-like model'
    _inherit = [
        'mail.thread.blacklist',
        'mail.thread.cc',
        'mail.activity.mixin',
    ]
    _mail_defaults_to_email = True
    _primary_email = 'email_from'

    name = fields.Char()
    company_id = fields.Many2one('res.company')
    user_id = fields.Many2one('res.users', tracking=1)
    email_from = fields.Char()
    customer_name = fields.Char()
    partner_id = fields.Many2one('res.partner', tracking=2)
    lang_code = fields.Char()
    mobile = fields.Char()
    phone = fields.Char()

    def _creation_message(self):
        self.ensure_one()
        return _('A new lead has been created and is assigned to %(user_name)s.', user_name=self.user_id.name or _('nobody'))

    def _get_customer_information(self):
        email_normalized_to_values = super()._get_customer_information()

        for lead in self:
            email_key = lead.email_normalized or lead.email
            values = email_normalized_to_values.setdefault(email_key, {})
            values['lang'] = values.get('lang') or lead.lang_code
            values['name'] = values.get('name') or lead.customer_name or parse_contact_from_email(lead.email_from)[0] or lead.email_from
            values['mobile'] = values.get('mobile') or lead.mobile
            values['phone'] = values.get('phone') or lead.phone
        return email_normalized_to_values

    def _message_get_suggested_recipients(self):
        recipients = super()._message_get_suggested_recipients()
        # check if that language is correctly installed (and active) before using it
        lang_code = self.env['res.lang']._get_data(code=self.lang_code).code or None
        if self.partner_id:
            self._message_add_suggested_recipient(
                recipients, partner=self.partner_id, reason=_('Customer'))
        elif self.email_from:
            self._message_add_suggested_recipient(
                recipients, email=self.email_from, reason=_('Customer Email'))
        return recipients

    def _message_post_after_hook(self, message, msg_vals):
        if self.email_from and not self.partner_id:
            # we consider that posting a message with a specified recipient (not a follower, a specific one)
            # on a document without customer means that it was created through the chatter using
            # suggested recipients. This heuristic allows to avoid ugly hacks in JS.
            new_partner = message.partner_ids.filtered(
                lambda partner: partner.email == self.email_from or (self.email_normalized and partner.email_normalized == self.email_normalized)
            )
            if new_partner:
                if new_partner[0].email_normalized:
                    email_domain = ('email_normalized', '=', new_partner[0].email_normalized)
                else:
                    email_domain = ('email_from', '=', new_partner[0].email)
                self.search([('partner_id', '=', False), email_domain]).write({'partner_id': new_partner[0].id})
        return super()._message_post_after_hook(message, msg_vals)
