# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class User(models.Model):
    _inherit = 'res.users'

    # -----------------------------------------
    # Business Methods
    # -----------------------------------------

    def _get_project_task_resource(self):
        return self.employee_id.resource_id
