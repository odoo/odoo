from odoo import exceptions, fields, models, tools


class MailTestAccess(models.Model):
    """ Test access on mail models without depending on real models like channel
    or partner which have their own set of ACLs. Public, portal and internal
    have access to this model depending on 'access' field, allowing to check
    ir.rule usage. """
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
    _inherit = ['mail.thread.blacklist']
    _mail_post_access = 'write'  # default value but ease mock
    _order = 'id DESC'
    _primary_email = 'email_from'

    name = fields.Char()
    email_from = fields.Char()
    phone = fields.Char()
    customer_id = fields.Many2one('res.partner', 'Customer')
    is_locked = fields.Boolean()

    def _mail_get_partner_fields(self):
        return ['customer_id']

    def _get_mail_message_access(self, res_ids, operation, model_name=None):
        # customize message creation
        if operation == "create":
            if any(record.is_locked for record in self.browse(res_ids)):
                raise exceptions.AccessError('Cannot post on locked records')
            else:
                return "read"
        return super()._get_mail_message_access(res_ids, operation, model_name=model_name)


class MailTestAccessPublic(models.Model):
    """A model inheriting from mail.thread with public read and write access
    to test some public and guest interactions."""
    _description = "Access Test Public"
    _name = "mail.test.access.public"
    _inherit = ["mail.thread"]

    name = fields.Char("Name")
    customer_id = fields.Many2one('res.partner', 'Customer')
    email = fields.Char('Email')
    mobile = fields.Char('Mobile')
    is_locked = fields.Boolean()

    def _mail_get_partner_fields(self):
        return ['customer_id']

    def _get_customer_information(self):
        email_key_to_values = super()._get_customer_information()
        for record in self.filtered('email'):
            # do not fill Falsy with random data, unless monorecord (= always correct)
            if not tools.email_normalize(record.email) and len(self) > 1:
                continue
            values = email_key_to_values.setdefault(record.email, {})
            if not values.get('mobile'):
                values['mobile'] = record.mobile
        return email_key_to_values
