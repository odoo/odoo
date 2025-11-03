from odoo import api, fields, models


class Test_Ir_Rules_Some_Obj(models.Model):
    _name = 'test_ir_rules.some_obj'
    _description = 'Object For Test Access Right'

    val = fields.Integer()
    categ_id = fields.Many2one('test_ir_rules.obj_categ')
    parent_id = fields.Many2one('test_ir_rules.some_obj')
    company_id = fields.Many2one('res.company')
    forbidden = fields.Integer(
        groups='test_orm.test_group,base.group_portal',
        default=5,
    )
    forbidden2 = fields.Integer(groups='test_orm.test_group')
    forbidden3 = fields.Integer(groups=fields.NO_ACCESS)


class Test_Ir_Rules_Container(models.Model):
    _name = 'test_ir_rules.container'
    _description = 'Test Access Right Container'

    some_ids = fields.Many2many('test_ir_rules.some_obj', 'test_ir_rules_rel', 'container_id', 'some_id')


class Test_Ir_Rules_Inherits(models.Model):
    _name = 'test_ir_rules.inherits'
    _description = 'Object for testing related access rights'

    _inherits = {'test_ir_rules.some_obj': 'some_id'}

    some_id = fields.Many2one('test_ir_rules.some_obj', required=True, ondelete='restrict')


class Test_Ir_Rules_Obj_Categ(models.Model):
    _name = 'test_ir_rules.obj_categ'
    _description = "Context dependent searchable model"

    name = fields.Char(required=True)

    @api.model
    def search_fetch(self, domain, field_names=None, offset=0, limit=None, order=None):
        if self.env.context.get('only_media'):
            domain += [('name', '=', 'Media')]
        return super().search_fetch(domain, field_names, offset, limit, order)
