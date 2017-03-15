# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import ValidationError
from odoo.modules.module import get_module_resource


_logger = logging.getLogger(__name__)


class Employee(models.Model):
    _inherit = "hr.employee"

    # resource
    org_chart_data = fields.Integer(string='Manager (org chart)', related="id", store=False)
    children_count = fields.Integer(string='Subordinates', compute="_count_children", store=True)

    @api.multi
    @api.depends('parent_id', 'child_ids')
    def _count_children(self):
        for employee in self:
            count = len(employee.child_ids)
            for c in employee.child_ids:
                count += c.children_count
            employee.children_count = count

    @api.multi
    def get_org_chart(self, manager=False):
        if not self:
            return {}
        self.ensure_one()

        to_data = lambda x: {'name': x.name, 'id': x.id, 'job': x.job_id and x.job_id.name or '', 'count': x.children_count}
        managers = []
        if manager: manager = self.browse(manager)
        i = 0
        # FIXME: workaround to test the prototype
        while manager and i<3:
            managers.insert(0, to_data(manager))
            manager = manager.parent_id
            i += 1

        result =  {
            'self': to_data(self),
            'managers': managers,
            'children': map(to_data, self.child_ids),
            'more_managers': manager and True or False,
        }
        print '='*50
        print result
        return result

