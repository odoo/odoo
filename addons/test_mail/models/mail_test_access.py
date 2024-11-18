from odoo import fields, models


class MailTestAccess(models.Model):
    """ Test access on mail models without depending on real models like channel
    or partner which have their own set of ACLs. Public, portal and internal
    have access to this model depending on 'access' field, allowing to check
    ir.rule usage. """
    _description = 'Access Test'
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


class MailTestAccessPublic(models.Model):
    """A model inheriting from mail.thread with public read and write access
    to test some public and guest interactions."""
    _description = "Access Test Public"
    _name = "mail.test.access.public"
    _inherit = ["mail.thread"]

    name = fields.Char("Name")
    customer_id = fields.Many2one('res.partner', 'Customer')
    is_locked = fields.Boolean()

    def _mail_get_partner_fields(self):
        return ['customer_id']
