# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models
from odoo.osv import expression


_logger = logging.getLogger(__name__)


class PlanningShift(models.Model):
    _inherit = 'planning.slot'

    project_id = fields.Many2one(
        'project.project', string="Project", compute='_compute_project_id', store=True,
        readonly=False, copy=True, check_company=True, group_expand='_read_group_project_id',
    )

    @api.depends('template_id.project_id')
    def _compute_project_id(self):
        for slot in self:
            if slot.template_id:
                slot.previous_template_id = slot.template_id
                if slot.template_id.project_id:
                    slot.project_id = slot.template_id.project_id
            elif slot.previous_template_id and not slot.template_id and slot.previous_template_id.project_id == slot.project_id:
                slot.project_id = False

    def _read_group_project_id(self, projects, domain, order):
        dom_tuples = [(dom[0], dom[1]) for dom in domain if isinstance(dom, list) and len(dom) == 3]
        if self._context.get('planning_expand_project') and ('start_datetime', '<=') in dom_tuples and ('end_datetime', '>=') in dom_tuples:
            if ('project_id', '=') in dom_tuples or ('project_id', 'ilike') in dom_tuples:
                filter_domain = self._expand_domain_m2o_groupby(domain, 'project_id')
                return self.env['project.project'].search(filter_domain, order=order)
            filters = expression.AND([[('project_id.active', '=', True)], self._expand_domain_dates(domain)])
            return self.env['planning.slot'].search(filters).mapped('project_id')
        return projects

    def _get_fields_breaking_publication(self):
        """ Fields list triggering the `publication_warning` to True when updating shifts """
        result = super(PlanningShift, self)._get_fields_breaking_publication()
        result.append('project_id')
        return result

    def _display_name_fields(self):
        return  super()._display_name_fields() + ['project_id']

    def _prepare_template_values(self):
        result = super(PlanningShift, self)._prepare_template_values()
        return {
            'project_id': self.project_id.id,
            **result
        }

    @api.model
    def _get_template_fields(self):
        values = super(PlanningShift, self)._get_template_fields()
        return {'project_id': 'project_id', **values}

    def _get_domain_template_slots(self):
        domain = super(PlanningShift, self)._get_domain_template_slots()
        if self.project_id:
            domain += ['|', ('project_id', '=', self.project_id.id), ('project_id', '=', False)]
        return domain

    @api.depends('role_id', 'employee_id', 'project_id')
    def _compute_template_autocomplete_ids(self):
        super(PlanningShift, self)._compute_template_autocomplete_ids()

    @api.depends('project_id')
    def _compute_template_id(self):
        super(PlanningShift, self)._compute_template_id()

    @api.depends('template_id', 'role_id', 'allocated_hours', 'project_id')
    def _compute_allow_template_creation(self):
        super(PlanningShift, self)._compute_allow_template_creation()

    @api.model_create_multi
    def create(self, vals_list):
        return super().create(vals_list)

    def write(self, values):
        return super(PlanningShift, self).write(values)

    def _prepare_shift_vals(self):
        return {
            **super()._prepare_shift_vals(),
            'project_id': self.project_id.id,
        }
