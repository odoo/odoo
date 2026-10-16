from odoo import api, fields, models


class TestOrmFieldsConversion(models.Model):
    _name = 'test_orm.fields_conversion'
    _description = 'Test ORM Fields Conversion'

    name = fields.Char()

    integer = fields.Integer()


class TestOrmFieldsConversionCompany(models.Model):
    _name = 'test_orm.fields_conversion.company_dependent'
    _description = 'Test ORM Fields Conversion Company'

    name = fields.Char()

    integer = fields.Integer(company_dependent=True)
