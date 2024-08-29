from odoo import fields, models


class ImportChar(models.Model):
    _description = 'Tests: Base Import Model, Character'

    value = fields.Char()


class ImportCharRequired(models.Model):
    _description = 'Tests: Base Import Model, Character required'

    value = fields.Char(required=True)


class ImportCharReadonly(models.Model):
    _description = 'Tests: Base Import Model, Character readonly'

    value = fields.Char(readonly=True)


class ImportCharNoreadonly(models.Model):
    _description = 'Tests: Base Import Model, Character No readonly'

    value = fields.Char(readonly=True)


class ImportCharStillreadonly(models.Model):
    _description = 'Tests: Base Import Model, Character still readonly'

    value = fields.Char(readonly=True)


# TODO: complex field (m2m, o2m, m2o)
class ImportM2o(models.Model):
    _description = 'Tests: Base Import Model, Many to One'

    value = fields.Many2one('import.m2o.related')


class ImportM2oRelated(models.Model):
    _description = 'Tests: Base Import Model, Many to One related'

    value = fields.Integer(default=42)


class ImportM2oRequired(models.Model):
    _description = 'Tests: Base Import Model, Many to One required'

    value = fields.Many2one('import.m2o.required.related', required=True)


class ImportM2oRequiredRelated(models.Model):
    _description = 'Tests: Base Import Model, Many to One required related'

    value = fields.Integer(default=42)


class ImportO2m(models.Model):
    _description = 'Tests: Base Import Model, One to Many'

    name = fields.Char()
    value = fields.One2many('import.o2m.child', 'parent_id')


class ImportO2mChild(models.Model):
    _description = 'Tests: Base Import Model, One to Many child'

    parent_id = fields.Many2one('import.o2m')
    value = fields.Integer()


class ImportPreview(models.Model):
    _description = 'Tests: Base Import Model Preview'

    name = fields.Char('Name')
    somevalue = fields.Integer(string='Some Value', required=True)
    othervalue = fields.Integer(string='Other Variable')


class ImportFloat(models.Model):
    _description = 'Tests: Base Import Model Float'

    value = fields.Float()
    value2 = fields.Monetary()
    currency_id = fields.Many2one('res.currency')


class ImportComplex(models.Model):
    _description = 'Tests: Base Import Model Complex'

    f = fields.Float()
    m = fields.Monetary()
    c = fields.Char()
    currency_id = fields.Many2one('res.currency')
    d = fields.Date()
    dt = fields.Datetime()
    parent_id = fields.Many2one('import.complex')
