from odoo import fields, models


class ForgeAccess(models.Model):
    _name = "forge.access"
    _description = "Forge Access"

    name = fields.Char(required=True)
    model_id = fields.Many2one("forge.model", required=True, ondelete="cascade")
    group_id = fields.Many2one("forge.group", ondelete="cascade")
    perm_read = fields.Boolean(default=True)
    perm_write = fields.Boolean(default=False)
    perm_create = fields.Boolean(default=False)
    perm_unlink = fields.Boolean(default=False)
