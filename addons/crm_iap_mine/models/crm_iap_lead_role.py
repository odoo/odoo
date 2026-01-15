# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CrmIapLeadRole(models.Model):
    """ CRM Reveal People Roles for People """
    _name = 'crm.iap.lead.role'
    _description = 'People Role'

    name = fields.Char(string='Role Name', required=True, translate=True)
    reveal_id = fields.Char(required=True)
    color = fields.Integer(string='Color Index')

    _name_uniq = models.Constraint(
        'unique (name)',
        'Role name already exists!',
    )

    def _compute_display_name(self):
        for role in self:
            role.display_name = (role.name or '').replace('_', ' ').title()
