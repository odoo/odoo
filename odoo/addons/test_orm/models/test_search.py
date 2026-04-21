from odoo import fields, models


class TestSearchInitialRelation(models.Model):
    _name = 'test_search.initial_rel'
    _description = 'Test Search Model Initial Relation'

    m2o_id = fields.Many2one('test_search.intermediate_rel')
    m2o_required_id = fields.Many2one('test_search.intermediate_rel', required=True)


class TestSearchIntermediateRelation(models.Model):
    _name = 'test_search.intermediate_rel'
    _description = 'Test Search Model Intermediate Relation'

    name = fields.Char()

    o2m_ids = fields.One2many('test_search.initial_rel', 'm2o_id')
    o2m_required_ids = fields.One2many('test_search.initial_rel', 'm2o_required_id')

    m2o_id = fields.Many2one('test_search.last_rel')
    m2o_required_id = fields.Many2one('test_search.last_rel', required=True)


class TestSearchLastRelation(models.Model):
    _name = 'test_search.last_rel'
    _description = 'Test Search Model Last Relation'

    name = fields.Char()

    o2m_ids = fields.One2many('test_search.intermediate_rel', 'm2o_id')
    o2m_required_ids = fields.One2many('test_search.intermediate_rel', 'm2o_required_id')


class TestOrmSearchOrderAlpha(models.Model):
    _name = 'test_orm.search.order.alpha'
    _description = 'Test ORM Search Order Alpha'

    name = fields.Char()
    beta_id = fields.Many2one('test_orm.search.order.beta')
    alpha_loop_id = fields.Many2one('test_orm.search.order.alpha')


class TestOrmSearchOrderBeta(models.Model):
    _name = 'test_orm.search.order.beta'
    _description = 'Test ORM Search Order Beta'

    name = fields.Char()
    alpha_id = fields.Many2one('test_orm.search.order.alpha')


class TestOrmSearchOrderPartner(models.Model):
    _name = 'test_orm.search.order.partner'
    _description = 'Test ORM Search Order Partner'
    _inherit = ['test_orm.partner']

    user_id = fields.Many2one('test_orm.search.order.users')


class TestOrmSearchOrderUsers(models.Model):
    _name = 'test_orm.search.order.users'
    _description = 'Test ORM Search Order Users'
    _inherits = {'test_orm.search.order.partner': 'partner_id'}

    login = fields.Char()
    partner_id = fields.Many2one('test_orm.search.order.partner', required=True, ondelete='restrict')
