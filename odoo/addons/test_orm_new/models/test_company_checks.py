from odoo import fields, models


class TestOrmCompanyChecksParent(models.Model):
    _name = 'test_orm.company_checks.parent'
    _description = 'Test ORM Company Checks Parent'

    name = fields.Char()
    company_id = fields.Many2one('res.company')


class TestOrmCompanyChecksChild(models.Model):
    _name = 'test_orm.company_checks.child'
    _description = 'Test ORM Company Checks Child'
    _check_company_auto = True

    name = fields.Char()
    company_id = fields.Many2one('res.company')
    parent_id = fields.Many2one('test_orm.company_checks.parent', string="Parent", check_company=True)
    parent_ids = fields.Many2many('test_orm.company_checks.parent', relation='test_orm_company_checks_child_parent_rel', string="Parents", check_company=True)


class TestOrmCompanyChecksChildNoCheck(models.Model):
    _name = 'test_orm.company_checks.child_no_check'
    _description = 'Test ORM Company Checks Child No Check'
    _check_company_auto = True

    name = fields.Char()
    company_id = fields.Many2one('res.company')
    parent_id = fields.Many2one('test_orm.company_checks.parent', check_company=False)
