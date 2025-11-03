from odoo import fields, models


class Test_Company_Checks_Parent(models.Model):
    _name = 'test_company_checks.parent'
    _description = 'Model Multicompany parent'

    name = fields.Char()
    company_id = fields.Many2one('res.company')


class Test_Company_Checks_Child(models.Model):
    _name = 'test_company_checks.child'
    _description = 'Model Multicompany child'
    _check_company_auto = True

    name = fields.Char()
    company_id = fields.Many2one('res.company')
    parent_id = fields.Many2one('test_company_checks.parent', string="Parent", check_company=True)
    parent_ids = fields.Many2many('test_company_checks.parent', string="Parents", check_company=True)


class Test_Company_Checks_Child_Nocheck(models.Model):
    _name = 'test_company_checks.child_nocheck'
    _description = 'Model Multicompany child'
    _check_company_auto = True

    name = fields.Char()
    company_id = fields.Many2one('res.company')
    parent_id = fields.Many2one('test_company_checks.parent', check_company=False)
    