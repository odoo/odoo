from odoo import fields, models


class TestAccessFeedbackSomeObj(models.Model):
    _name = 'test_access_feedback.some_obj'
    _description = 'Object For Test Access Right'

    val = fields.Integer()
    parent_id = fields.Many2one('test_access_feedback.some_obj')
    company_id = fields.Many2one('res.company')
    forbidden = fields.Integer(
        groups='test_orm.test_access_feedback_group,base.group_portal',
        default=5,
    )
    forbidden2 = fields.Integer(groups='test_orm.test_access_feedback_group')
    forbidden3 = fields.Integer(groups=fields.NO_ACCESS)


class TestAccessFeedbackInherits(models.Model):
    _name = 'test_access_feedback.inherits'
    _description = 'Object for testing related access rights'

    _inherits = {'test_access_feedback.some_obj': 'some_id'}

    some_id = fields.Many2one('test_access_feedback.some_obj', required=True, ondelete='restrict')


class TestAccessFeedbackChild(models.Model):
    _name = 'test_access_feedback.child'
    _description = 'Object for testing company ir rule'

    parent_id = fields.Many2one('test_access_feedback.some_obj')
