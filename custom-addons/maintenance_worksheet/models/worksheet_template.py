# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class WorksheetTemplate(models.Model):
    _inherit = 'worksheet.template'

    @api.model
    def _get_maintenance_request_manager_group(self):
        return self.env.ref('maintenance.group_equipment_manager')

    @api.model
    def _get_maintenance_request_user_group(self):
        return self.env.ref('base.group_user')

    @api.model
    def _get_maintenance_request_access_all_groups(self):
        return self.env.ref('maintenance.group_equipment_manager')

    @api.model
    def _get_maintenance_request_module_name(self):
        return 'maintenance_worksheet'

    @api.model
    def _get_models_to_check_dict(self):
        res = super()._get_models_to_check_dict()
        res['maintenance.request'] = [('maintenance.request', 'Maintenance Request')]
        return res
