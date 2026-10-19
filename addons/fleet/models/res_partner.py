# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    partner_cars_count = fields.Integer(
        compute="_compute_partner_cars_count",
        string="Cars Count"
    )

    def _compute_partner_cars_count(self):
        rg = self.env['fleet.vehicle.assignation.log']._read_group([
            ('driver_id', 'in', self.ids),
        ], ['driver_id'], ['__count'])
        cars_count = {driver.id: count for driver, count in rg}
        for partner in self:
            partner.partner_cars_count = cars_count.get(partner.id, 0)

    def action_open_partner_cars(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "fleet.vehicle.assignation.log",
            "views": [[self.env.ref("fleet.fleet_vehicle_assignation_log_view_list").id, "list"],
                      [False, "form"]],
            "domain": [("driver_id", "in", self.ids)],
            "context": dict(self.env.context, default_driver_id=self.id),
            "name": self.env._("Cars History"),
        }
