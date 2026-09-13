from odoo import fields, models


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    tag_ids = fields.Many2many(comodel_name="document.tag")
    folder_id = fields.Many2one(
        comodel_name="document.document",
        domain="[('type', '=', 'folder'), ('shortcut_document_id', '=', False)]",
        help="By defining a folder, the upload activities will generate a document",
    )
