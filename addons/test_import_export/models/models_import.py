from odoo import fields, models, api


class ImportChar(models.Model):
    _name = 'import.char'
    _description = 'Tests: Base Import Model, Character'

    value = fields.Char()


class ImportCharRequired(models.Model):
    _name = 'import.char.required'
    _description = 'Tests: Base Import Model, Character required'

    value = fields.Char(required=True)


class ImportCharReadonly(models.Model):
    _name = 'import.char.readonly'
    _description = 'Tests: Base Import Model, Character readonly'

    value = fields.Char(readonly=True)


class ImportCharNoreadonly(models.Model):
    _name = 'import.char.noreadonly'
    _description = 'Tests: Base Import Model, Character No readonly'

    value = fields.Char(readonly=True)


class ImportCharStillreadonly(models.Model):
    _name = 'import.char.stillreadonly'
    _description = 'Tests: Base Import Model, Character still readonly'

    value = fields.Char(readonly=True)


# TODO: complex field (m2m, o2m, m2o)
class ImportM2o(models.Model):
    _name = 'import.m2o'
    _description = 'Tests: Base Import Model, Many to One'

    value = fields.Many2one('import.m2o.related')


class ImportM2oRelated(models.Model):
    _name = 'import.m2o.related'
    _description = 'Tests: Base Import Model, Many to One related'

    value = fields.Integer(default=42)


class ImportM2oRequired(models.Model):
    _name = 'import.m2o.required'
    _description = 'Tests: Base Import Model, Many to One required'

    value = fields.Many2one('import.m2o.required.related', required=True)


class ImportM2oRequiredRelated(models.Model):
    _name = 'import.m2o.required.related'
    _description = 'Tests: Base Import Model, Many to One required related'

    value = fields.Integer(default=42)


class ImportO2m(models.Model):
    _name = 'import.o2m'
    _description = 'Tests: Base Import Model, One to Many'

    name = fields.Char()
    value = fields.One2many('import.o2m.child', 'parent_id')


class ImportO2mChild(models.Model):
    _name = 'import.o2m.child'
    _description = 'Tests: Base Import Model, One to Many child'

    name = fields.Char()
    parent_id = fields.Many2one('import.o2m')
    value = fields.Integer()


class ImportPreview(models.Model):
    _name = 'import.preview'
    _description = 'Tests: Base Import Model Preview'

    name = fields.Char('Name')
    somevalue = fields.Integer(string='Some Value', required=True)
    othervalue = fields.Integer(string='Other Variable')
    date = fields.Date(string='Date')
    datetime = fields.Datetime(string='Datetime')


class ImportFloat(models.Model):
    _name = 'import.float'
    _description = 'Tests: Base Import Model Float'

    value = fields.Float()
    value2 = fields.Monetary()
    currency_id = fields.Many2one('res.currency')


class ImportComplex(models.Model):
    _name = 'import.complex'
    _description = 'Tests: Base Import Model Complex'

    f = fields.Float()
    m = fields.Monetary()
    c = fields.Char()
    currency_id = fields.Many2one('res.currency')
    d = fields.Date()
    dt = fields.Datetime()
    parent_id = fields.Many2one('import.complex')
    html = fields.Html()


class ImportPropertiesDefinition(models.Model):
    _name = 'import.properties.definition'
    _description = 'import.properties.definition'
    _rec_name = 'id'

    properties_definition = fields.PropertiesDefinition()
    record_properties_ids = fields.One2many('import.properties', 'record_definition_id')
    main_properties_record_id = fields.Many2one('import.properties', 'record_definition_id')


class ImportProperties(models.Model):
    _name = 'import.properties'
    _description = 'import.properties'

    properties = fields.Properties(definition='record_definition_id.properties_definition')
    record_definition_id = fields.Many2one('import.properties.definition')


class PropertyInherits(models.Model):
    _name = _description = 'import.properties.inherits'
    _inherits = {'import.properties': 'parent_id'}

    parent_id = fields.Many2one('import.properties', required=True, ondelete="cascade")


class PathToProperty(models.Model):
    _name = _description = 'import.path.properties'

    properties_id = fields.Many2one('import.properties')
    another_properties_id = fields.Many2one('import.properties')
    all_properties_ids = fields.Many2many('import.properties', compute='_compute_all_import_properties')

    @api.depends('properties_id', 'another_properties_id')
    def _compute_all_import_properties(self):
        for record in self:
            record.all_properties_ids = record.properties_id | record.another_properties_id
