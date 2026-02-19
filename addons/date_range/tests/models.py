from odoo import fields, models


class TestDateRangeSearchMixin(models.Model):
    _name = "test.date.range.search.mixin"
    _inherit = ["date.range.search.mixin"]
    _date_range_search_field = "test_date"

    name = fields.Char()
    test_date = fields.Date()
