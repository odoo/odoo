
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def _create_revision_bom(self, will_update_version=True):
        revision_bom = super()._create_revision_bom(will_update_version)
        # Copies the operations' steps.
        if revision_bom and self.workorder_ids.check_ids:
            for operation in revision_bom.operation_ids:
                operation_values = (operation['company_id'], operation['name'], operation['workcenter_id'])
                original_operation = self.bom_id.operation_ids.filtered(lambda op: operation_values == (op['company_id'], op['name'], op['workcenter_id']))
                for step in original_operation.quality_point_ids:
                    operation.quality_point_ids += step.copy()
        return revision_bom
