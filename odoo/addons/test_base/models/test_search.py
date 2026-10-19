from odoo import fields, models


class TestOrmSearchTopRelation(models.Model):
    _name = 'test_orm.search.top_rel'
    _description = 'Test Search Model Top Relation'

    mid_rel_id = fields.Many2one('test_orm.search.mid_rel')
    mid_rel_req_id = fields.Many2one('test_orm.search.mid_rel', required=True)


class TestOrmSearchMiddleRelation(models.Model):
    _name = 'test_orm.search.mid_rel'
    _description = 'Test Search Model Middle Relation'

    name = fields.Char()

    top_rel_ids = fields.One2many('test_orm.search.top_rel', 'mid_rel_id')
    top_rel_req_ids = fields.One2many('test_orm.search.top_rel', 'mid_rel_req_id')

    bot_rel_id = fields.Many2one('test_orm.search.bot_rel')
    bot_rel_req_id = fields.Many2one('test_orm.search.bot_rel', required=True)


class TestOrmSearchBottomRelation(models.Model):
    _name = 'test_orm.search.bot_rel'
    _description = 'Test Search Model Bottom Relation'

    name = fields.Char()

    mid_rel_ids = fields.One2many('test_orm.search.mid_rel', 'bot_rel_id')
    mid_rel_req_ids = fields.One2many('test_orm.search.mid_rel', 'bot_rel_req_id')


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
