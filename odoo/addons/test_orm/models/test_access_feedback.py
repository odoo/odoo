from odoo import api, fields, models


class Test_Access_Feedback_Some_Obj(models.Model):
    _name = 'test_access_feedback.some_obj'
    _description = 'Object For Test Access Right'

    val = fields.Integer()
    categ_id = fields.Many2one('test_access_feedback.obj_categ')
    parent_id = fields.Many2one('test_access_feedback.some_obj')
    company_id = fields.Many2one('res.company')
    forbidden = fields.Integer(
        groups='test_orm.test_group,base.group_portal',
        default=5,
    )
    forbidden2 = fields.Integer(groups='test_orm.test_group')
    forbidden3 = fields.Integer(groups=fields.NO_ACCESS)


class Test_Access_Feedback_Inherits(models.Model):
    _name = 'test_access_feedback.inherits'
    _description = 'Object for testing related access rights'

    _inherits = {'test_access_feedback.some_obj': 'some_id'}

    some_id = fields.Many2one('test_access_feedback.some_obj', required=True, ondelete='restrict')


class Test_Access_Feedback_Child(models.Model):
    _name = 'test_access_feedback.child'
    _description = 'Object for testing company ir rule'

    parent_id = fields.Many2one('test_access_feedback.some_obj')


class Test_Access_Feedback_Obj_Categ(models.Model):
    _name = 'test_access_feedback.obj_categ'
    _description = "Context dependent searchable model"

    name = fields.Char(required=True)

    @api.model
    def search_fetch(self, domain, field_names=None, offset=0, limit=None, order=None):
        if self.env.context.get('only_media'):
            domain += [('name', '=', 'Media')]
        return super().search_fetch(domain, field_names, offset, limit, order)
