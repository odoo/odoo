from odoo import models, fields


class FuzzerModel(models.Model):
    _name = 'test.fuzzer.model'
    _description = 'Test fuzzer model'
    _rec_name = 'n'  # For name_create.

    n = fields.Char()
