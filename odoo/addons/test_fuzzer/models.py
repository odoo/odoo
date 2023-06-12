from odoo import models, fields


class FuzzerModel(models.Model):
    _name = 'test.fuzzer.model'
    _description = 'Test fuzzer model'
    _rec_name = 'char'  # For name_create.

    char = fields.Char(string='char')
    char_translate = fields.Char(string='char_translate', translate=True)
    text = fields.Text(string='text')
    integer = fields.Integer(string='integer')
    selection = fields.Selection(string='selection', selection=[('1', '1'), ('2', '2'), ('3', '3')])
    boolean = fields.Boolean(string='boolean')
    float = fields.Float(string='float')
    html = fields.Html(string='html')
    date = fields.Date(string='date')
    datetime = fields.Datetime(string='datetime')
    binary = fields.Binary(string='binary')
    many2one = fields.Many2one(string='many2one', comodel_name='test.fuzzer.model')
    one2many = fields.One2many(string='one2many', comodel_name='test.fuzzer.model', inverse_name='many2one')
