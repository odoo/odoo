from odoo import models, fields


class Thread(models.Model):
    _name = 'test_fetchmail.thread'
    _inherit = ['mail.thread']

    name = fields.Text()
