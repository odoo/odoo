# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _


class User(models.Model):
    _inherit = ['res.users']

    spouse_fiscal_status = fields.Selection(related='employee_ids.spouse_fiscal_status', readonly=False)
    disabled = fields.Boolean(related='employee_ids.disabled', readonly=False)
    disabled_spouse_bool = fields.Boolean(related='employee_ids.disabled_spouse_bool', readonly=False)
    disabled_children_bool = fields.Boolean(related='employee_ids.disabled_children_bool', readonly=False)
    resident_bool = fields.Boolean(related='employee_ids.resident_bool', readonly=False)
    disabled_children_number = fields.Integer(related='employee_ids.disabled_children_number', readonly=False)
    dependent_children = fields.Integer(related='employee_ids.dependent_children', readonly=False)
    other_dependent_people = fields.Boolean(related='employee_ids.other_dependent_people', readonly=False)
    other_senior_dependent = fields.Integer(related='employee_ids.other_senior_dependent', readonly=False)
    other_disabled_senior_dependent = fields.Integer(related='employee_ids.other_disabled_senior_dependent', readonly=False)
    other_juniors_dependent = fields.Integer(related='employee_ids.other_juniors_dependent', readonly=False)
    other_disabled_juniors_dependent = fields.Integer(related='employee_ids.other_disabled_juniors_dependent', readonly=False)
    dependent_seniors = fields.Integer(related='employee_ids.dependent_seniors', readonly=False)
    dependent_juniors = fields.Integer(related='employee_ids.dependent_juniors', readonly=False)
    spouse_net_revenue = fields.Float(related='employee_ids.spouse_net_revenue', readonly=False)
    spouse_other_net_revenue = fields.Float(related='employee_ids.spouse_other_net_revenue', readonly=False)

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights.
            Access rights are disabled by default, but allowed
            on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        l10n_be_payroll_readable_fields = [
            'spouse_fiscal_status',
            'disabled',
            'disabled_spouse_bool',
            'disabled_children_bool',
            'resident_bool',
            'disabled_children_number',
            'dependent_children',
            'other_dependent_people',
            'other_senior_dependent',
            'other_disabled_senior_dependent',
            'other_juniors_dependent',
            'other_disabled_juniors_dependent',
            'dependent_seniors',
            'dependent_juniors',
            'spouse_net_revenue',
            'spouse_other_net_revenue',
        ]
        init_res = super(User, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        type(self).SELF_READABLE_FIELDS = type(self).SELF_READABLE_FIELDS + l10n_be_payroll_readable_fields
        type(self).SELF_WRITEABLE_FIELDS = type(self).SELF_WRITEABLE_FIELDS + l10n_be_payroll_readable_fields
        return init_res
