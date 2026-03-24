from odoo import fields, models


class TestFieldsMisc(models.Model):
    _name = 'test_fields.misc'
    _description = 'Test Fields Misc'

    boolean = fields.Boolean()
    boolean_true = fields.Boolean(default=True)
    boolean_false = fields.Boolean(default=False)
    json_default = fields.Json(default={'values': []})


class TestFieldsNumeric(models.Model):
    _name = 'test_fields.numeric'
    _description = 'Test Fields Numeric'

    integer = fields.Integer()
    float = fields.Float()
    float_digits = fields.Float(digits=(16, 2))
    float_3 = fields.Float(digits=(10, 2), default=3.14)
    float_4 = fields.Float(digits='ORM Precision')


class TestFieldsRelational(models.Model):
    _name = 'test_fields.relational'
    _description = 'Test Fields Relational'

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.EUR'))


class TestFieldsTemporal(models.Model):
    _name = 'test_fields.temporal'
    _description = 'Test Fields Temporal'

    date = fields.Date()
    datetime = fields.Datetime()


class TestFieldsTextual(models.Model):
    _name = 'test_fields.textual'
    _description = 'Test Fields Textual'

    char = fields.Char()
    html_sanitize_false = fields.Html(sanitize=False)
    text = fields.Text()


class TestFieldsAll(models.Model):
    _name = 'test_fields.all'
    _description = 'Test Fields All'
    _inherit = [
        'test_fields.misc',
        'test_fields.numeric',
        'test_fields.relational',
        'test_fields.temporal',
        'test_fields.textual',
    ]
