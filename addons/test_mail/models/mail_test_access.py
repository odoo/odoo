from odoo import exceptions, fields, models


class MailTestAccess(models.Model):
    """ Test access on mail models without depending on real models like channel
    or partner which have their own set of ACLs. """
    _description = 'Mail Access Test'
    _name = 'mail.test.access'
    _inherit = ['mail.thread.blacklist']
    _mail_post_access = 'write'  # default value but ease mock
    _order = 'id DESC'
    _primary_email = 'email_from'

    name = fields.Char()
    email_from = fields.Char()
    phone = fields.Char()
    customer_id = fields.Many2one('res.partner', 'Customer')
    access = fields.Selection(
        [
            ('public', 'public'),
            ('logged', 'Logged'),
            ('logged_ro', 'Logged readonly for portal'),
            ('followers', 'Followers'),
            ('internal', 'Internal'),
            ('internal_ro', 'Internal readonly'),
            ('admin', 'Admin'),
        ],
        name='Access', default='public')

    def _mail_get_partner_fields(self):
        return ['customer_id']


class MailTestAccessCusto(models.Model):
    """ Test access on mail models without depending on real models like channel
    or partner which have their own set of ACLs. """
    _description = 'Mail Access Test with Custo'
    _name = 'mail.test.access.custo'
    _inherit = ['mail.thread.blacklist', 'mail.activity.mixin']
    _mail_post_access = 'write'  # default value but ease mock
    _order = 'id DESC'
    _primary_email = 'email_from'

    name = fields.Char()
    email_from = fields.Char()
    phone = fields.Char()
    customer_id = fields.Many2one('res.partner', 'Customer')
    is_locked = fields.Boolean()
    is_readonly = fields.Boolean()

    def _mail_get_partner_fields(self):
        return ['customer_id']

    def _get_mail_message_access(self, res_ids, operation, model_name=None):
        # customize message creation: only unlocked, except admins
        if operation == "create":
            if any(record.is_locked for record in self.browse(res_ids)) and not self.env.user._is_admin():
                raise exceptions.AccessError('Cannot post on locked records')
            return "read"
        # customize read: read access on unlocked, write access on locked
        elif operation == "read":
            if any(record.is_locked for record in self.browse(res_ids)):
                return "write"
            return "read"
        return super()._get_mail_message_access(res_ids, operation, model_name=model_name)
