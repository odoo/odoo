from odoo import fields, models


class Char(models.Model):
    _name = 'import.char'
    _description = 'Tests: Base Import Model, Character'

    value = fields.Char()


class CharRequired(models.Model):
    _name = 'import.char.required'
    _description = 'Tests: Base Import Model, Character required'

    value = fields.Char(required=True)


class CharReadonly(models.Model):
    _name = 'import.char.readonly'
    _description = 'Tests: Base Import Model, Character readonly'

    value = fields.Char(readonly=True)


class CharNoreadonly(models.Model):
    _name = 'import.char.noreadonly'
    _description = 'Tests: Base Import Model, Character No readonly'

    value = fields.Char(readonly=True)


class CharStillreadonly(models.Model):
    _name = 'import.char.stillreadonly'
    _description = 'Tests: Base Import Model, Character still readonly'

    value = fields.Char(readonly=True)


# TODO: complex field (m2m, o2m, m2o)
class M2o(models.Model):
    _name = 'import.m2o'
    _description = 'Tests: Base Import Model, Many to One'

    value = fields.Many2one('import.m2o.related')


class M2oRelated(models.Model):
    _name = 'import.m2o.related'
    _description = 'Tests: Base Import Model, Many to One related'

    value = fields.Integer(default=42)


class M2oRequired(models.Model):
    _name = 'import.m2o.required'
    _description = 'Tests: Base Import Model, Many to One required'

    value = fields.Many2one('import.m2o.required.related', required=True)


class M2oRequiredRelated(models.Model):
    _name = 'import.m2o.required.related'
    _description = 'Tests: Base Import Model, Many to One required related'

    value = fields.Integer(default=42)


class O2m(models.Model):
    _name = 'import.o2m'
    _description = 'Tests: Base Import Model, One to Many'

    name = fields.Char()
    value = fields.One2many('import.o2m.child', 'parent_id')


class O2mChild(models.Model):
    _name = 'import.o2m.child'
    _description = 'Tests: Base Import Model, One to Many child'

    parent_id = fields.Many2one('import.o2m')
    value = fields.Integer()


class Preview(models.Model):
    _name = 'import.preview'
    _description = 'Tests: Base Import Model Preview'

    name = fields.Char('Name')
    somevalue = fields.Integer(string='Some Value', required=True)
    othervalue = fields.Integer(string='Other Variable')


class Float(models.Model):
    _name = 'import.float'
    _description = 'Tests: Base Import Model Float'

    value = fields.Float()
    value2 = fields.Monetary()
    currency_id = fields.Many2one('res.currency')


class Complex(models.Model):
    _name = 'import.complex'
    _description = 'Tests: Base Import Model Complex'

    f = fields.Float()
    m = fields.Monetary()
    c = fields.Char()
    currency_id = fields.Many2one('res.currency')
    d = fields.Date()
    dt = fields.Datetime()
    parent_id = fields.Many2one('import.complex')


class PropertyDefinition(models.Model):
    _name = _description = 'import.properties.definition'
    _rec_name = 'id'

    properties_definition = fields.PropertiesDefinition()
    record_properties_ids = fields.One2many('import.properties', 'record_definition_id')
    main_properties_record_id = fields.Many2one('import.properties', 'record_definition_id')


class Property(models.Model):
    _name = _description = 'import.properties'

    properties = fields.Properties(definition='record_definition_id.properties_definition')
    record_definition_id = fields.Many2one('import.properties.definition')
