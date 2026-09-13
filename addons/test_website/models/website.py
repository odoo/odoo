from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    some_translatable_field = fields.Char(
        string="A translatable field",
        translate=True,
        default="something",
    )

    def _search_get_details(self, search_type, order, options):
        result = super()._search_get_details(search_type, order, options)
        if search_type == "test":
            result.append(
                self.env["test.model"]._search_get_detail(self, order, options)
            )
        return result
