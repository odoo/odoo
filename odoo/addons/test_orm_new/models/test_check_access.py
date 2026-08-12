from odoo import fields, models


class TestOrmCheckAccess(models.Model):
    """We want to simulate a record that would typically be accessed by a portal user,
       with a relational field to records that could not be accessed by a portal user.
    """
    _name = 'test_orm.check_access'
    _description = 'Test ORM Check Access'

    name = fields.Char()
    message_partner_ids = fields.Many2many(comodel_name='res.partner')
