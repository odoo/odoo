from markupsafe import Markup

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


class TestOrmNormalized(models.Model):
    _name = 'test_orm.normalized'
    _description = 'Test ORM Normalized Fields'

    name = fields.Char(normalize=lambda name: name and name.strip().upper())
    label = fields.Char(translate=True, normalize=lambda label: label and label.strip())
    count = fields.Integer(normalize=lambda count: max(count, 0))
    code = fields.Char(compute='_compute_code', store=True, readonly=False, normalize=lambda code: code and code.replace('-', ''))
    # normalize receives a Markup, like the record value
    body = fields.Html(normalize=lambda body: body and Markup('<p>%s</p>') % body.striptags())
    amount = fields.Float(digits=(16, 2), normalize=abs)
    state = fields.Selection([('a', 'A'), ('b', 'B')], normalize=lambda state: state and state.lower())
    day = fields.Date(normalize=lambda day: day and day.replace(day=1))
    moment = fields.Datetime(normalize=lambda moment: moment and moment.replace(second=0))
    # empty values are normalized, too
    title = fields.Char(translate=True, normalize=lambda title: title or 'Untitled')
    data = fields.Json(normalize=lambda data: data and {key: val for key, val in data.items() if val is not None})

    @api.depends('name')
    def _compute_code(self):
        for record in self:
            record.code = record.name and f'-{record.name}-'
