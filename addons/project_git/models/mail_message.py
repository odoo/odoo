from odoo import fields, models


class MailMessage(models.Model):
    _inherit = "mail.message"

    git_base_sha = fields.Char(index=True)
    git_head_sha = fields.Char(index=True)
    git_file_path = fields.Char(index=True)
    git_old_line = fields.Integer()
    git_new_line = fields.Integer()
    git_side = fields.Selection(
        [("old", "Old"), ("new", "New")],
        default="new",
    )
    git_hunk_header = fields.Char()
