from openerp import fields, models

class SomeObj(models.Model):
    _name = 'test_access_right.some_obj'

    val = fields.Integer()


class Container(models.Model):
    _name = 'test_access_right.container'

    some_ids = fields.Many2many('test_access_right.some_obj', 'test_access_right_rel', 'container_id', 'some_id')
