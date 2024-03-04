from odoo import fields, models


class Message(models.Model):
    """ Models a localizable message, i.e. any textual content to be translated.
        Messages are retrieved from a Resource.
        A Message localized to a specific Language becomes a Translation.
    """
    _name = "t9n.message"
    _description = "Localizable message"

    body = fields.Text(
        help="The actual, textual content to be translated.",
    )
    resource_id = fields.Many2one(
        comodel_name="t9n.resource",
        help="The resource (typically a file) from which the entry is coming from."
    )
    translation_ids = fields.One2many(
        comodel_name="t9n.translation",
        inverse_name="source_id",
        string="Translations",
    )
