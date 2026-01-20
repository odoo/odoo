from odoo import fields, models


class TestOrmModel_Parent(models.Model):
    _name = 'test_orm.model_parent'
    _description = 'Model Multicompany parent'

    name = fields.Char()
    company_id = fields.Many2one('res.company')


class TestOrmModel_Child(models.Model):
    _name = 'test_orm.model_child'
    _description = 'Model Multicompany child'
    _check_company_auto = True

    name = fields.Char()
    company_id = fields.Many2one('res.company')
    parent_id = fields.Many2one('test_orm.model_parent', string="Parent", check_company=True)
    parent_ids = fields.Many2many('test_orm.model_parent', string="Parents", check_company=True)


class TestOrmModel_Child_Nocheck(models.Model):
    _name = 'test_orm.model_child_nocheck'
    _description = 'Model Multicompany child'
    _check_company_auto = True

    name = fields.Char()
    company_id = fields.Many2one('res.company')
    parent_id = fields.Many2one('test_orm.model_parent', check_company=False)
