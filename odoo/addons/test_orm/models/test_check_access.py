from odoo import api, fields, models


class Test_Check_Access_Ticket(models.Model):
    """We want to simulate a record that would typically be accessed by a portal user,
       with a relational field to records that could not be accessed by a portal user.
    """
    _name = 'test_check_access.ticket'
    _description = 'Fake ticket For Test Access Right'

    name = fields.Char()
    message_partner_ids = fields.Many2many(comodel_name='res.partner')
