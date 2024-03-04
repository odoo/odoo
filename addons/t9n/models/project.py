from odoo import fields, models


class Project(models.Model):
    """ A project is a collection of Resources to be localized into a given set
        of Languages.
    """
    _name = "t9n.project"
    _description = "Translation project"

    src_lang_id = fields.Many2one(
        comodel_name="t9n.language",
        string="Source Language",
        help="The original language of the messages you want to translate."
    )
    resource_ids = fields.One2many(
        comodel_name="t9n.resource",
        inverse_name="project_id",
        string="Resources",
    )
    target_lang_ids = fields.Many2many(
        comodel_name="t9n.language",
        string="Languages",
        help="The list of languages into which the project can be translated.",
    )
