# -*- coding: utf-8 -*-
from odoo import fields, models


class ActWindowView(models.Model):
    _inherit = 'ir.actions.act_window.view'

    view_mode = fields.Selection(selection_add=[
        ('gallery', "Awesome Gallery")
    ],  ondelete={'gallery': 'cascade'})
