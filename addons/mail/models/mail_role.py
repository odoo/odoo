from odoo import fields, models


class MailRole(models.Model):
    _name = "mail.role"
    _description = "Role in Mail"

    name = fields.Char(required=True, translate=True)
    user_ids = fields.Many2many("res.users", string="Users")

    _unique_name = models.UniqueIndex("(name)", "A role with the same name already exists.")
