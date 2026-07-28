from odoo import api, fields, models


class TestOrmFields(models.Model):
    _name = 'test_orm.fields'
    _description = 'Test ORM Fields'

    name = fields.Char()
    computed_name = fields.Char(compute='_compute_computed_name')
    parent_id = fields.Many2one('test_orm.fields')
    child_ids = fields.One2many('test_orm.fields', 'parent_id')
    inversed_x2many = fields.Many2one('test_orm.fields.relations', compute='_compute_inversed_x2many', inverse='_inverse_inversed_x2many')

    @api.depends('name')
    def _compute_computed_name(self):
        for record in self:
            record.computed_name = f'computed {record.name}'

    def _compute_inversed_x2many(self):
        pass

    def _inverse_inversed_x2many(self):
        pass


class TestOrmFieldsRelations(models.Model):
    _name = 'test_orm.fields.relations'
    _description = 'Test ORM Fields Relations'

    name = fields.Char()


class TestOrmFieldsPartner(models.Model):
    _name = 'test_orm.fields.partner'
    _description = 'Test ORM Fields Partner'
    _allow_sudo_commands = False

    name = fields.Char()
    email = fields.Char()
    vat = fields.Char(compute='_compute_vat')
    country_id = fields.Many2one('test_orm.fields.country')
    user_ids = fields.One2many('test_orm.fields.users', 'partner_id')

    def _compute_vat(self):
        self.vat = 'Tax ID'


class TestOrmFieldsCountry(models.Model):
    _name = 'test_orm.fields.country'
    _description = 'Test ORM Fields Country'

    name = fields.Char(required=True)


class TestOrmFieldsUsers(models.Model):
    _name = 'test_orm.fields.users'
    _description = 'Test ORM Fields Users'
    _inherits = {'test_orm.fields.partner': 'partner_id'}
    _allow_sudo_commands = False

    name = fields.Char(related='partner_id.name', inherited=True, readonly=False)
    partner_id = fields.Many2one('test_orm.fields.partner', required=True, ondelete='restrict')
