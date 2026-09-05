from odoo import api, fields, models


class TestAccessFeedback(models.Model):
    _name = 'test_orm.access_feedback'
    _description = 'Object For Test Access Right'

    val = fields.Integer()
    parent_id = fields.Many2one('test_orm.access_feedback')
    company_id = fields.Many2one('res.company')
    forbidden = fields.Integer(
        groups='test_orm_new.test_access_feedback_group,base.group_portal',
        default=5,
    )
    forbidden2 = fields.Integer(groups='test_orm_new.test_access_feedback_group')
    forbidden3 = fields.Integer(groups=fields.NO_ACCESS)
    active = fields.Boolean(default=True)
    child_ids = fields.One2many('test_orm.access_feedback.child', 'parent_id')


class TestAccessFeedbackInherits(models.Model):
    _name = 'test_orm.access_feedback.inherits'
    _description = 'Object for testing related access rights'

    _inherits = {'test_orm.access_feedback': 'some_id'}

    some_id = fields.Many2one('test_orm.access_feedback', required=True, ondelete='restrict')


class TestAccessFeedbackChild(models.Model):
    _name = 'test_orm.access_feedback.child'
    _description = 'Object for testing company ir rule'

    parent_id = fields.Many2one('test_orm.access_feedback')
