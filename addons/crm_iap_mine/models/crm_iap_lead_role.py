# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PeopleRole(models.Model):
    """ CRM Reveal People Roles for People """
    _name = 'crm.iap.lead.role'
    _description = 'People Role'

    name = fields.Char(string='Role Name', required=True, translate=True)
    reveal_id = fields.Char(required=True)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Role name already exists!'),
    ]

    @api.depends('name')
    def _compute_display_name(self):
        for role in self:
            role.display_name = role.name.replace('_', ' ').title()


class PeopleSeniority(models.Model):
    """ Seniority for People Rules """
    _name = 'crm.iap.lead.seniority'
    _description = 'People Seniority'

    name = fields.Char(string='Name', required=True, translate=True)
    reveal_id = fields.Char(required=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Name already exists!'),
    ]

    @api.depends('name')
    def _compute_display_name(self):
        for seniority in self:
            seniority.display_name = seniority.name.replace('_', ' ').title()
