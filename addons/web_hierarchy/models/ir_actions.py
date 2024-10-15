# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import base


class IrActionsAct_WindowView(base.IrActionsAct_WindowView):

    view_mode = fields.Selection(selection_add=[('hierarchy', 'Hierarchy')], ondelete={'hierarchy': 'cascade'})
