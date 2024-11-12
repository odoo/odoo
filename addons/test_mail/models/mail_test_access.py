from odoo import fields, models


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
