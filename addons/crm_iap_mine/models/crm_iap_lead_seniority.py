# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CrmIapLeadSeniority(models.Model):
    """ Seniority for People Rules """
    _description = 'People Seniority'

    name = fields.Char(string='Name', required=True, translate=True)
    reveal_id = fields.Char(required=True)

    _name_uniq = models.Constraint(
        'unique (name)',
        'Name already exists!',
    )

    @api.depends('name')
    def _compute_display_name(self):
        for seniority in self:
            seniority.display_name = (seniority.name or '').replace('_', ' ').title()
