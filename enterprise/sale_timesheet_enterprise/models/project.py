# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Project(models.Model):
    _inherit = 'project.project'

    def action_profitability_items(self, section_name, domain=None, res_id=False):
        action = super().action_profitability_items(section_name, domain, res_id)
        if section_name in ['billable_fixed', 'billable_time', 'billable_milestones', 'billable_manual', 'non_billable']:
            grid_view = self.env.ref('sale_timesheet_enterprise.timesheet_view_grid_by_invoice_type').id
            action['views'] = [
                (view_id, view_type) if view_type != 'grid' else (grid_view or view_id, view_type)
                for view_id, view_type in action['views']
            ]
        return action
