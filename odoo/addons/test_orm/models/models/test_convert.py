from odoo import api, fields, models


class TestConvertTestModel(models.Model):
    _name = 'test_convert.test_model'
    _description = "Test Convert Model"

    name = fields.Char(translate=True)
    usered_ids = fields.One2many('test_convert.usered', 'test_id')


class TestConvertUsered(models.Model):
    _name = 'test_convert.usered'
    _description = "z test model ignore"

    name = fields.Char()
    test_id = fields.Many2one('test_convert.test_model')

    @api.model
    def model_method(self, *args, **kwargs):
        return self, args, kwargs

    def method(self, *args, **kwargs):
        return self, args, kwargs
