# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


L10N_BE_PAYROLL_READABLE_FIELDS = [
    'spouse_fiscal_status_explanation',
]
L10N_BE_PAYROLL_WRITABLE_FIELDS = [
    'spouse_fiscal_status',
    'disabled',
    'disabled_spouse_bool',
    'disabled_children_bool',
    'disabled_children_number',
    'dependent_children',
    'other_dependent_people',
    'other_senior_dependent',
    'other_disabled_senior_dependent',
    'other_juniors_dependent',
    'other_disabled_juniors_dependent',
    'dependent_seniors',
    'dependent_juniors',
    'l10n_be_scale_seniority',
]


class User(models.Model):
    _inherit = ['res.users']

    spouse_fiscal_status = fields.Selection(related='employee_ids.spouse_fiscal_status', readonly=False)
    spouse_fiscal_status_explanation = fields.Char(related='employee_ids.spouse_fiscal_status_explanation')
    disabled = fields.Boolean(related='employee_ids.disabled', readonly=False)
    disabled_spouse_bool = fields.Boolean(related='employee_ids.disabled_spouse_bool', readonly=False)
    disabled_children_bool = fields.Boolean(related='employee_ids.disabled_children_bool', readonly=False)
    disabled_children_number = fields.Integer(related='employee_ids.disabled_children_number', readonly=False)
    dependent_children = fields.Integer(related='employee_ids.dependent_children', readonly=False)
    other_dependent_people = fields.Boolean(related='employee_ids.other_dependent_people', readonly=False)
    other_senior_dependent = fields.Integer(related='employee_ids.other_senior_dependent', readonly=False)
    other_disabled_senior_dependent = fields.Integer(related='employee_ids.other_disabled_senior_dependent', readonly=False)
    other_juniors_dependent = fields.Integer(related='employee_ids.other_juniors_dependent', readonly=False)
    other_disabled_juniors_dependent = fields.Integer(related='employee_ids.other_disabled_juniors_dependent', readonly=False)
    dependent_seniors = fields.Integer(related='employee_ids.dependent_seniors', readonly=False)
    dependent_juniors = fields.Integer(related='employee_ids.dependent_juniors', readonly=False)
    l10n_be_scale_seniority = fields.Integer(related='employee_id.l10n_be_scale_seniority', readonly=False, related_sudo=False)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + L10N_BE_PAYROLL_READABLE_FIELDS + L10N_BE_PAYROLL_WRITABLE_FIELDS

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + L10N_BE_PAYROLL_WRITABLE_FIELDS
