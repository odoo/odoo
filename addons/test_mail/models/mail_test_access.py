from odoo import fields, models, tools


class MailTestAccess(models.Model):
    """Test access on mail models without depending on real models like channel
    or partner which have their own set of ACLs. Public, portal and internal
    have access to this model depending on 'access' field, allowing to check
    ir.rule usage."""

    _description = "Mail Access Test"
    _name = "mail.test.access"
    _inherit = ["mixin.mail.thread.blacklist"]
    _mail_post_access = "write"  # default value but ease mock
    _order = "id DESC"
    _primary_email = "email_from"
    _mail_partner_fields = ("customer_id",)

    name = fields.Char()
    email_from = fields.Char()
    phone_ids = fields.Many2many(comodel_name="phone.number")
    customer_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
    )
    access = fields.Selection(
        selection=[
            ("public", "public"),
            ("logged", "Logged"),
            ("logged_ro", "Logged readonly for portal"),
            ("followers", "Followers"),
            ("internal", "Internal"),
            ("internal_ro", "Internal readonly"),
            ("admin", "Admin"),
        ],
        default="public",
        name="Access",
    )


class MailTestAccessCusto(models.Model):
    """Test access on mail models without depending on real models like channel
    or partner which have their own set of ACLs."""

    _description = "Mail Access Test with Custo"
    _name = "mail.test.access.custo"
    _inherit = ["mixin.mail.thread.blacklist", "mixin.mail.activity"]
    _mail_post_access = "write"  # default value but ease mock
    _order = "id DESC"
    _primary_email = "email_from"
    _mail_partner_fields = ("customer_id",)

    name = fields.Char()
    email_from = fields.Char()
    phone_ids = fields.Many2many(comodel_name="phone.number")
    customer_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
    )
    is_locked = fields.Boolean()
    is_readonly = fields.Boolean()

    def _mail_get_operation_for_mail_message_operation(self, message_operation):
        # customize message creation: only unlocked, except admins
        if message_operation == "create" and not self.env.user._is_admin():
            return dict.fromkeys(self.filtered(lambda r: not r.is_locked), "read")
        # customize read: read access on unlocked, write access on locked
        elif message_operation == "read":
            return {record: "write" if record.is_locked else "read" for record in self}
        return super()._mail_get_operation_for_mail_message_operation(message_operation)


class MailTestAccessPublic(models.Model):
    """A model inheriting from mixin.mail.thread with public read and write access
    to test some public and guest interactions."""

    _description = "Access Test Public"
    _name = "mail.test.access.public"
    _inherit = ["mixin.mail.thread"]
    _mail_partner_fields = ("customer_id",)

    name = fields.Char(string="Name")
    customer_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
    )
    email = fields.Char(string="Email")
    phone_ids = fields.Many2many(comodel_name="phone.number")
    is_locked = fields.Boolean()

    def _mail_get_customer_information(self):
        email_key_to_values = super()._mail_get_customer_information()
        for record in self.filtered("email"):
            # do not fill Falsy with random data, unless monorecord (= always correct)
            if not tools.email_normalize(record.email) and len(self) > 1:
                continue
            values = email_key_to_values.setdefault(record.email, {})
            if not values.get("phone"):
                values["phone"] = record.phone_ids[:1].number
        return email_key_to_values
