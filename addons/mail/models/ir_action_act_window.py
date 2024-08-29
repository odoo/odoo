# -*- coding: utf-8 -*-
from odoo.addons import base
from odoo import fields, models


class IrActionsActWindowView(models.Model, base.IrActionsActWindowView):
    _name = "ir.actions.act_window.view"


    view_mode = fields.Selection(selection_add=[
        ('activity', 'Activity')
    ], ondelete={'activity': 'cascade'})
