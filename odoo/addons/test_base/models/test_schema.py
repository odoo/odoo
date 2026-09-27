from odoo import fields, models


class TestOrmSchema(models.Model):
    _name = 'test_orm.schema'
    _description = 'Test ORM Schema'
    _inherit = ['test_orm.mixed']

    # Properties Fields
    properties = fields.Properties()
    properties_definition = fields.PropertiesDefinition()

    # Attributes
    required = fields.Char(required=True)
    size = fields.Char(size=3)
    index_btree = fields.Char(index='btree')
    index_btree_not_null = fields.Char(index='btree_not_null')
    index_trigram = fields.Char(index='trigram')
    very_very_very_very_very_long_field_name_1 = fields.Integer(index=True)
    very_very_very_very_very_long_field_name_2 = fields.Integer(index=True)


class TestOrmSchemaTable(models.Model):
    _name = 'test_orm.schema_table'
    _description = 'Test ORM Schema Table'

    boolean = fields.Boolean()
    char = fields.Char()
    integer = fields.Integer()
    float = fields.Float()


class TestSchemaConflictingIndex(models.Model):
    # This model is used to set up 'test_schema' conflicting indexes.
    _name = 'test_orm.schema_index'
    _description = 'Test Schema Index'

    btree = fields.Char(index=True)
