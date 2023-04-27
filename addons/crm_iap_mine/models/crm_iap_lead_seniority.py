# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


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
