# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import project

from odoo import api, models


class ProjectTaskRecurrence(models.Model, project.ProjectTaskRecurrence):

    @api.model
    def _get_recurring_fields_to_copy(self):
        return super()._get_recurring_fields_to_copy() + ['so_analytic_account_id']
