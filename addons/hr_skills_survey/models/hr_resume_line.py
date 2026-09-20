from odoo import fields, models


class HrResumeLine(models.Model):
    _inherit = "hr.resume.line"

    survey_id = fields.Many2one(
        comodel_name="survey.survey",
        string="Certification",
        readonly=True,
    )

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [
            dict(vals, name=self.env._("%s (copy)", resume_line.name))
            for resume_line, vals in zip(self, vals_list, strict=True)
        ]

    def copy_translations(self, new, excluded=()):
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new, "name", lambda record, term: record.env._("%s (copy)", term)
        )
