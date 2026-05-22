# from odoo import models
from odoo.models import Model

from odoo import fields

class TestModel(Model):
    _name = 'estate_test_model'
    _description = 'Test model for Estate module'
    # _order: 'sequence'

    estate_name = fields.Char('Test estate name', required=True, translate=True)