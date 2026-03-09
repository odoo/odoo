from odoo import fields, models


class DummyResUsers(models.Model):
    _name = 'dummy.res.users'
    _description = 'dummy.res.users'

    name = fields.Char()
    group_ids = fields.Many2many('dummy.res.groups', column1='uid', column2='gid')
    partner_id = fields.Many2one('dummy.res.partner')


class DummyResGroups(models.Model):
    _name = 'dummy.res.groups'
    _description = 'dummy.res.groups'

    name = fields.Char()
    user_ids = fields.Many2many('dummy.res.users', column1='gid', column2='uid')


class DummyResCompany(models.Model):
    _name = 'dummy.res.company'
    _description = 'dummy.res.company'

    name = fields.Char()
    partner_id = fields.Many2one('dummy.res.partner')


class DummyResCountry(models.Model):
    _name = 'dummy.res.country'
    _description = 'dummy.res.country'

    name = fields.Char()
    state_ids = fields.One2many('dummy.res.country.state', inverse_name='country_id')


class DummyResCountryState(models.Model):
    _name = 'dummy.res.country.state'
    _description = 'dummy.res.country.state'

    name = fields.Char()
    country_id = fields.Many2one('dummy.res.country')


class DummyResPartner(models.Model):
    _name = 'dummy.res.partner'
    _description = 'dummy.res.partner'

    name = fields.Char()
    active = fields.Boolean(default=True)
    employee = fields.Boolean()
    function = fields.Char()
    vat_label = fields.Char(compute='_compute_vat_label')
    contact_address = fields.Char(compute='_compute_contact_address')
    country_id = fields.Many2one('dummy.res.country')
    state_id = fields.Many2one('dummy.res.country.state')
    type_ref = fields.Reference(selection=[('dummy.res.partner.type', 'Dummy type')])
    user_id = fields.Many2one('dummy.res.users')
    user_ids = fields.One2many('dummy.res.users', inverse_name='partner_id')
    company_id = fields.Many2one('dummy.res.company')
    category_id = fields.Many2many('dummy.res.partner.category', column1='partner_id', column2='category_id')
    parent_id = fields.Many2one('dummy.res.partner')
    child_ids = fields.One2many('dummy.res.partner', inverse_name='parent_id')
    bank_ids = fields.One2many('dummy.res.partner.bank', inverse_name='partner_id')

    def _compute_vat_label(self):
        self.vat_label = 'vat_label'

    def _compute_contact_address(self):
        self.contact_address = 'contact_address'


class DummyResPartnerType(models.Model):
    _name = 'dummy.res.partner.type'
    _description = 'dummy.res.partner.type'

    name = fields.Char()


class DummyResPartnerCategory(models.Model):
    _name = 'dummy.res.partner.category'
    _description = 'dummy.res.partner.category'

    name = fields.Char()
    active = fields.Boolean(default=True)
    parent_id = fields.Many2one('dummy.res.partner.category')
    child_ids = fields.One2many('dummy.res.partner.category', inverse_name='parent_id')
    partner_ids = fields.Many2many('dummy.res.partner', column1='category_id', column2='partner_id')


class DummyResPartnerBank(models.Model):
    _name = 'dummy.res.partner.bank'
    _description = 'dummy.res.partner.bank'

    name = fields.Char()
    account_number = fields.Char()
    partner_id = fields.Many2one('dummy.res.partner')
