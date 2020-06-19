# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import AccessError


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', copy=False, ondelete='set null',
        check_company=True, help="Analytic account to which this vehicle is linked for financial management.")

    def action_generate_analytic_account(self):
        if not self.env.user.has_group('fleet.fleet_group_user'):
            raise AccessError(_("Sorry, you must be at least a fleet user to make this action."))
        for vehicle in self:
            analytic_account = self.env['account.analytic.account'].sudo().create([{
                'name': self._get_analytic_name(),
                'company_id': self.company_id.id or self.env.company.id,
            }])
            vehicle.write({'analytic_account_id': analytic_account.id})
