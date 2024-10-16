# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.addons import base


class IrActionsAct_WindowView(base.IrActionsAct_WindowView):

    view_mode = fields.Selection(selection_add=[
        ('activity', 'Activity')
    ], ondelete={'activity': 'cascade'})
