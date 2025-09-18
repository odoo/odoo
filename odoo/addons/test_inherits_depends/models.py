from odoo import fields, models


# We add a field on this model
class TestUnit(models.Model):
    _inherit = "test.unit"

    second_name = fields.Char()
