from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class Project(models.Model):
    """A project is a collection of Resources to be localized into a given set
    of Languages.
    """

    _name = "t9n.project"
    _description = "Translation project"

    name = fields.Char("Project", required=True)
    src_lang_id = fields.Many2one(
        comodel_name="t9n.language",
        string="Source Language",
        help="The original language of the messages you want to translate.",
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

    @api.constrains("src_lang_id", "target_lang_ids")
    def _check_source_and_target_languages(self):
        for record in self:
            if record.src_lang_id in record.target_lang_ids:
                raise ValidationError(_("A project's target languages must be different from its source language."))
