from odoo import fields, models


class IndexChangeLog(models.Model):
    _name = "missing.index_log"
    _description = "actions taken on indexes"
    _rec_name = "index_command"

    index_command = fields.Char(string="Index command", required=True)
    index_name = fields.Char(string="Index name", required=True)
    action = fields.Selection([("created", "Created"), ("removed", "Removed")], required=True, string="Action taken")
