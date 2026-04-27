# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import models


class IrActions(models.Model):
    _name = 'ir.actions.actions'
    _inherit = 'ir.actions.actions'

    def _get_actions_by_type(self):
        """
        Returns:
            A dict of {type: [action]} of actions in this recordset
            mapped to their concrete model type.
        """
        # map: type -> concrete actions
        return {
            action_type: self.env[action_type].browse(actions.ids)
            for action_type, actions in self.grouped('type').items()
        }
