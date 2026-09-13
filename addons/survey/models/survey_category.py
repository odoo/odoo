from odoo import fields, models


class SurveyCategory(models.Model):
    _name = "survey.category"
    _description = "Survey Category"
    _inherit = ["mixin.tag"]
    _order = "sequence, name"

    name = fields.Char(string="Category Name")
    sequence = fields.Integer(default=10)
    survey_count = fields.Integer(
        string="Surveys",
        compute="_compute_survey_count",
    )

    def _compute_survey_count(self) -> None:
        read_group_res = self.env["survey.survey"]._read_group(
            [("category_id", "in", self.ids)],
            ["category_id"],
            ["__count"],
        )
        data = {category.id: count for category, count in read_group_res}
        for category in self:
            category.survey_count = data.get(category.id, 0)
