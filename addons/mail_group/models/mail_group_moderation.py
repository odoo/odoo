from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import email_normalize


class MailGroupModeration(models.Model):
    _name = "mail.group.moderation"
    _description = "Mailing List black/white list"

    email = fields.Char(required=True)
    status = fields.Selection(
        selection=[("allow", "Always Allow"), ("ban", "Permanent Ban")],
        default="ban",
        required=True,
    )
    mail_group_id = fields.Many2one(
        comodel_name="mail.group",
        string="Group",
        index=True,
        required=True,
        ondelete="cascade",
    )

    _mail_group_email_uniq = models.Constraint(
        "UNIQUE(mail_group_id, email)",
        "You can create only one rule for a given email address in a group.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            email_normalized = email_normalize(values.get("email"))
            if not email_normalized:
                raise UserError(_("Invalid email address “%s”", values.get("email")))
            values["email"] = email_normalized
        return super().create(vals_list)

    def write(self, vals):
        if "email" in vals:
            email_normalized = email_normalize(vals["email"])
            if not email_normalized:
                raise UserError(_("Invalid email address “%s”", vals.get("email")))
            vals["email"] = email_normalized
        return super().write(vals)
