from odoo import fields, models


class TestReadGroupOverrideOrder(models.Model):
    _name = 'test_read_group_override.order'
    _description = 'Sales order'

    many2one_id = fields.Many2one('test_read_group_override.order')
