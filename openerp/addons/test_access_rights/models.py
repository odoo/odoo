from openerp import fields, models

class SomeObj(models.Model):
    _name = 'test_access_right.some_obj'

    val = fields.Integer()
