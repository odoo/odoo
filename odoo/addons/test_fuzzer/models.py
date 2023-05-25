from odoo import models, fields


class FuzzerModel(models.Model):
    _name = 'test.fuzzer.model'
    _description = 'Test fuzzer model'

    n = fields.Integer()
