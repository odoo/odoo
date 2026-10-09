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


class TestOrmFieldsConversionContext(models.Model):
    _name = 'test_orm.fields_conversion.context_dependent'
    _description = 'Test ORM Fields Conversion Context'

    name = fields.Char()

    integer = fields.Integer(compute='_compute_integer', store=True, depends_context=('foo',))

    @api.depends('name')
    def _compute_integer(self):
        for record in self:
            if value := record.env.context.get('foo'):
                record.integer = value
            else:
                record.integer = 0
