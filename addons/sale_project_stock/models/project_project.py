# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    def _get_picking_action(self, action_name, picking_type=None):
        result = super()._get_picking_action(action_name, picking_type)

        if picking_type and (property_warehouse := self.env.user.property_warehouse_id):
            if picking_type == 'outgoing':
                result['context']['default_picking_type_id'] = property_warehouse.out_type_id.id
            elif picking_type == 'incoming':
                result['context']['default_picking_type_id'] = property_warehouse.in_type_id.id

        return result
