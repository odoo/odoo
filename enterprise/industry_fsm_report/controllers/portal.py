# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.addons.industry_fsm.controllers.portal import CustomerPortal


class CustomerFsmPortal(CustomerPortal):

    def _get_worksheet_data(self, task_sudo):
        data = super()._get_worksheet_data(task_sudo)
        worksheet_map = {}
        if task_sudo.worksheet_template_id:
            x_model = task_sudo.worksheet_template_id.model_id.model
            worksheet = request.env[x_model].sudo().search([('x_project_task_id', '=', task_sudo.id)], limit=1, order="create_date DESC")  # take the last one
            worksheet_map[task_sudo.id] = worksheet
        data.update({'worksheet_map': worksheet_map})
        return data

    def _task_get_page_view_values(self, task, access_token, **kwargs):
        data = super()._task_get_page_view_values(task, access_token, **kwargs)
        worksheet_map = self._get_worksheet_data(task)
        data.update(worksheet_map)
        return data
