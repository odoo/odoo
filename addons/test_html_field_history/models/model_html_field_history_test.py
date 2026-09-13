from odoo import fields, models


class HtmlFieldHistoryTest(models.Model):
    _name = "html.field.history.test"
    _description = "Test html_field_history Model"
    _inherit = ["mixin.html.field.history"]

    def _get_fields_versioned(self):
        return [
            HtmlFieldHistoryTest.versioned_field_1.name,
            HtmlFieldHistoryTest.versioned_field_2.name,
        ]

    versioned_field_1 = fields.Html(string="vf1")
    versioned_field_2 = fields.Html(
        string="vf2",
        sanitize=False,
    )
