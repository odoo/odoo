# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.addons.resource.models.utils import filter_domain_leaf
from odoo.osv import expression

class PlanningSlot(models.Model):
    _inherit = 'planning.slot'

    employee_skill_ids = fields.One2many(related='employee_id.employee_skill_ids', string='Skills')

    @api.model
    def _group_expand_resource_id(self, resources, domain):
        """
        overriding
        _group_expand_resource_id adds 'resource_ids' in the domain corresponding to 'employee_skill_ids' fields already in the domain
        """
        # 1. Transform the current domain to search hr.skill records
        skill_search_domain = filter_domain_leaf(
            domain,
            lambda field: field == 'employee_skill_ids',
            field_name_mapping={'employee_skill_ids': 'name'}
        )
        if not skill_search_domain:
            return super()._group_expand_resource_id(resources, domain)

        # 2. Get matching employee_ids for every employee_skill_id found in the initial domain
        skill_ids = self.env['hr.skill']._search(skill_search_domain)
        employee_skill_read_group = self.env['hr.employee.skill']._read_group(
            [('skill_id', 'in', skill_ids)],
            [],
            ['employee_id:array_agg'],
        )
        matching_employee_ids = employee_skill_read_group[0][0]

        # 3. Looking for corresponding resources
        matching_resource_ids = self.env['resource.resource']._search([('employee_id', 'in', matching_employee_ids)])

        filtered_domain = expression.AND([
            [('resource_id', 'in', matching_resource_ids)],
            domain,
        ])
        return super()._group_expand_resource_id(resources, filtered_domain)
