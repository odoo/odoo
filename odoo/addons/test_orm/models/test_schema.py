from odoo import fields, models


class TestOrmSchema(models.Model):
    _name = 'test_orm.schema'
    _description = 'Test ORM Schema'

    currency_id = fields.Many2one('res.currency')  # Needed for the monetary field.
    res_model = fields.Char()  # Needed for the many2one_reference field.

    # Binary Fields
    binary_with_attachment = fields.Binary()
    binary_without_attachment = fields.Binary(attachment=False)
    image_with_attachment = fields.Image()
    image_without_attachment = fields.Image(attachment=False)

    # Misc Fields
    boolean = fields.Boolean()
    json = fields.Json()

    # Numeric Fields
    integer = fields.Integer()
    float_double_precision = fields.Float()
    float_numeric = fields.Float(digits=(0, False))
    monetary = fields.Monetary()

    # Properties Fields
    properties = fields.Properties()
    properties_definition = fields.PropertiesDefinition()

    # Reference Fields
    reference = fields.Reference(selection=[('option_1', 'Option 1')])
    many2one_reference = fields.Many2oneReference(model_field='res_model')

    # Relational Fields
    many2one_id = fields.Many2one(comodel_name='test_orm.schema_relations')
    one2many_ids = fields.One2many(comodel_name='test_orm.schema_relations', inverse_name='many2one_id')
    many2many_ids = fields.Many2many(comodel_name='test_orm.schema_relations')

    # Selection Fields
    selection = fields.Selection(selection=[('option_1', 'Option 1')])

    # Temporal Fields
    date = fields.Date()
    datetime = fields.Datetime()

    # Textual Fields
    char = fields.Char()
    html = fields.Html()
    text = fields.Text()

    # Attributes
    required = fields.Char(required=True)
    size = fields.Char(size=3)
    index_btree = fields.Char(index='btree')
    index_btree_not_null = fields.Char(index='btree_not_null')
    index_trigram = fields.Char(index='trigram')
    very_very_very_very_very_long_field_name_1 = fields.Integer(index=True)
    very_very_very_very_very_long_field_name_2 = fields.Integer(index=True)


class TestSchemaRelations(models.Model):
    # This model is used to set up 'test_schema' relations.
    _name = 'test_orm.schema_relations'
    _description = 'Test Schema Relations'

    many2one_id = fields.Many2one(comodel_name='test_orm.schema')
    one2many_ids = fields.One2many(comodel_name='test_orm.schema', inverse_name='many2one_id')
    many2many_ids = fields.Many2many(comodel_name='test_orm.schema')


class TestSchemaConflictingIndex(models.Model):
    # This model is used to set up 'test_schema' conflicting indexes.
    _name = 'test_orm.schema_index'
    _description = 'Test Schema Index'

    btree = fields.Char(index=True)
