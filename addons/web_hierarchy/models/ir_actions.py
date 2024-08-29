# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import base

from odoo import fields, models


class IrActionsActWindowView(models.Model, base.IrActionsActWindowView):
    _name = "ir.actions.act_window.view"


    view_mode = fields.Selection(selection_add=[('hierarchy', 'Hierarchy')], ondelete={'hierarchy': 'cascade'})
