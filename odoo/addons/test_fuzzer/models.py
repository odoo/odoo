from odoo import models, fields


class FuzzerModel(models.Model):
    _name = 'test.fuzzer.model'
    _description = 'Test fuzzer model'
    _rec_name = 'char'  # Required for the `name_create` method.

    char = fields.Char(string='char')
    char_translate = fields.Char(string='char_translate', translate=True)
