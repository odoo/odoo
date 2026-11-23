from odoo import models


class Client(models.Model):
    _inherit = 'owner'
    _name = 'client'
    _description = 'Client'