# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class WorkLocation(models.Model):
    _inherit = "hr.work.location"

    def _domain_fleet_manager_id(self):
        fleet_users = self.env.ref('fleet.fleet_group_user')
        domain = str(('id', 'in', fleet_users.users.ids))
        return f"[('company_ids', '=', company_id), {domain}]"

    fleet_manager_id = fields.Many2one('res.users', string='Default Fleet Manager', domain=_domain_fleet_manager_id)
