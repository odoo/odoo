from odoo import api, fields, models


class TestOrmIrRules(models.Model):
    _name = 'test_orm.ir_rules'
    _description = 'Test ORM ir_rules'

    val = fields.Integer()
    categ_id = fields.Many2one('test_orm.ir_rules.category')
    parent_id = fields.Many2one('test_orm.ir_rules')
    company_id = fields.Many2one('res.company')
    forbidden = fields.Integer(
        groups='test_orm_new.test_ir_rules_group,base.group_portal',
        default=5,
    )
    forbidden2 = fields.Integer(groups='test_orm_new.test_ir_rules_group')
    forbidden3 = fields.Integer(groups=fields.NO_ACCESS)
    active = fields.Boolean(default=True)
    child_ids = fields.One2many('test_orm.ir_rules.child', 'parent_id')


class TestOrmIrRulesCategory(models.Model):
    _name = 'test_orm.ir_rules.category'
    _description = "Test ORM ir_rules Category"

    name = fields.Char(required=True)

    @api.model
    def search_fetch(self, domain, field_names=None, offset=0, limit=None, order=None):
        if self.env.context.get('only_media'):
            domain += [('name', '=', 'Media')]
        return super().search_fetch(domain, field_names, offset, limit, order)


class TestOrmIrRulesChild(models.Model):
    _name = 'test_orm.ir_rules.child'
    _description = 'Test ORM ir_rules Child'

    parent_id = fields.Many2one('test_orm.ir_rules')


class TestOrmIrRulesContainer(models.Model):
    _name = 'test_orm.ir_rules.container'
    _description = 'Test ORM ir_rules Container'

    some_ids = fields.Many2many('test_orm.ir_rules', 'test_orm_ir_rules_rel', 'container_id', 'some_id')


class TestOrmIrRulesInherits(models.Model):
    _name = 'test_orm.ir_rules.inherits'
    _description = 'Test ORM ir_rules Inherits'

    _inherits = {'test_orm.ir_rules': 'some_id'}

    some_id = fields.Many2one('test_orm.ir_rules', required=True, ondelete='restrict')

