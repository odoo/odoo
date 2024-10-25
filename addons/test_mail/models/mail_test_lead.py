from odoo import fields, models, _


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
    email_from = fields.Char()
    customer_name = fields.Char()
    partner_id = fields.Many2one('res.partner')
    mobile = fields.Char()
    phone = fields.Char()
    user_id = fields.Many2one('res.users')

    def _creation_message(self):
        self.ensure_one()
        return _('A new lead has been created and is assigned to %(user_name)s.', user_name=self.user_id.name or _('nobody'))
