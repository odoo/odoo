import re

from odoo import api, fields, models


def _sanitize_account_number(account_number):
    if account_number:
        return re.sub(r'\W+', '', account_number).upper()
    return False


class TestOrmDomainExpressionPartner(models.Model):
    _name = 'test_orm.domain_expression.partner'
    _description = 'Test ORM Domain Expression Partner'

    def _default_category(self):
        return self.env['test_orm.partner.category'].browse(self.env.context.get('category_id'))

    name = fields.Char(required=True)
    email = fields.Char()
    active = fields.Boolean(default=True)
    website = fields.Char()
    vat = fields.Char(compute='_compute_vat')
    commercial_partner_id = fields.Many2one('test_orm.domain_expression.partner', compute='_compute_commercial_partner', store=True, recursive=True)
    category_id = fields.Many2many('test_orm.partner.category', relation='test_orm_domain_expression_partner_category_rel', column1='partner_id', column2='category_id', default=_default_category)
    user_ids = fields.One2many('test_orm.users', 'partner_id', string="user_ids")
    parent_id = fields.Many2one('test_orm.domain_expression.partner')
    child_ids = fields.One2many('test_orm.domain_expression.partner', 'parent_id')
    bank_ids = fields.One2many('test_orm.domain_expression.partner.bank', 'partner_id')
    country_id = fields.Many2one('test_orm.domain_expression.country')
    state_id = fields.Many2one('test_orm.domain_expression.country.state', domain="[('country_id', '=?', country_id)]")

    @api.depends('parent_id.commercial_partner_id', 'parent_id')
    def _compute_commercial_partner(self):
        for partner in self:
            if not partner.parent_id:
                partner.commercial_partner_id = partner
            else:
                partner.commercial_partner_id = partner.parent_id.commercial_partner_id


class TestOrmDomainExpressionPartnerBank(models.Model):
    _name = 'test_orm.domain_expression.partner.bank'
    _rec_name = 'account_number'
    _description = 'Test ORM Domain Expression Partner Bank'

    account_number = fields.Char(search='_search_account_number')
    sanitized_account_number = fields.Char(compute='_compute_sanitized_account_number', readonly=True, store=True)
    partner_id = fields.Many2one(comodel_name='test_orm.domain_expression.partner', domain=['|', ('is_company', '=', True), ('parent_id', '=', False)], required=True)

    @api.depends('account_number')
    def _compute_sanitized_account_number(self):
        for account in self:
            account.sanitized_account_number = _sanitize_account_number(account.account_number)

    def _search_account_number(self, operator, value):
        if operator in ('in', 'not in'):
            value = [_sanitize_account_number(i) for i in value]
        else:
            value = _sanitize_account_number(value)
        return [('sanitized_account_number', operator, value)]


class TestOrmDomainExpressionCountry(models.Model):
    _name = 'test_orm.domain_expression.country'
    _description = 'Test ORM Domain Expression Country'
    _order = 'name, id'

    name = fields.Char(required=True, translate=True)
    code = fields.Char()
    phone_code = fields.Integer()
    state_ids = fields.One2many('test_orm.domain_expression.country.state', 'country_id')


class TestOrmDomainExpressionCountryState(models.Model):
    _name = 'test_orm.domain_expression.country.state'
    _description = 'Test ORM Domain Expression Country State'

    name = fields.Char(required=True)
    code = fields.Char()
    country_id = fields.Many2one('test_orm.domain_expression.country', required=True)


class TestOrmDomainExpressionUsers(models.Model):
    _name = 'test_orm.domain_expression.users'
    _description = 'Test ORM Domain Expression Users'
    _inherits = {'test_orm.partner': 'partner_id'}

    name = fields.Char(required=True)
    partner_id = fields.Many2one('test_orm.partner', required=True, ondelete='restrict')
