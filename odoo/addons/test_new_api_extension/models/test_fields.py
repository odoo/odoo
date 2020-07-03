from odoo import api, fields, models
from odoo.exceptions import ValidationError

class DummyModel(models.Model):
    _inherit = 'test_new_api.dummy'
    _description = 'basic model with two fields (with & without defaults)'

    new_computed_field = fields.Char(required=True, store=True, compute="_compute_field")

    # Test everything works fine when adding new computed required stored field to an existing model
    def _compute_field(self):
        self.new_computed_field = "new"
