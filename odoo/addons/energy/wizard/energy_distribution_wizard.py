# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date

cached_property = {
    "contract": [],
    "d_order": [],
    "d_order_line": [],
}


class EnergyDistributionWizard(models.TransientModel):
    _name = "energy.distribution.wizard"
    _description = 'Energy Distribution'

    contract_id = fields.Many2one('contract', string='Contract')
    delivery_point_id = fields.Many2one('border', string='Contract Delivery Point', readonly=1)
    power_date = fields.Date(string='Power Date', required=True)
    distribution_line_ids = fields.Many2many('distribution.order.line', string='Distribution Lines')

    @api.onchange('power_date')
    def _default_line_ids(self):
        power_date = self.power_date
        if not power_date:
            self.distribution_line_ids = []
            return

        changed_power_date = self._origin.power_date
        contract_id = self.env.context.get('active_id')
        contract_type = self.env.context.get('contract_type')
        # create a new transit contract if it does not exist
        transit_contract_id = self.env["contract"].search([
            ("is_transit", "=", True),
            ("position", "=", contract_type),
            ("parent_contract_id", "=", contract_id),
            ("start_date", "=", power_date),
        ])
        if not transit_contract_id:
            transit_contract_id = self.env["contract"].create({
                "is_transit": True,
                "position": contract_type,
                "parent_contract_id": contract_id,
                "start_date": power_date,
            })
            if changed_power_date and changed_power_date != self.power_date:
                cached_property["contract"].append(transit_contract_id.id)
        distribution_ids = []
        for i in range(1, 25):
            distribution_id = self.env["distribution.order"].search([
                ("contract_id", "=", transit_contract_id.id),
                ("power_date", "=", power_date),
                ("power_hour", "=", i),
            ])
            if not distribution_id:
                distribution_id = self.env["distribution.order"].create({
                    "contract_id": transit_contract_id.id,
                    "power_date": power_date,
                    "power_hour": i,
                })
                if changed_power_date and changed_power_date != self.power_date:
                    cached_property["d_order"].append(distribution_id.id)
            for border in self.env["border"].search([("id", "!=", self.delivery_point_id.id)]):
                distribution_id.write({"distribution_line_ids": [(0, 0, {
                        'contract_id': transit_contract_id.id,
                        'delivery_point_id': border.id,
                        'distribution_id': distribution_id.id,
                        'power_date': self.power_date,
                        'power_hour': i,
                        'power': 0.0,
                    })]})
            distribution_ids.append(distribution_id.id)
            if changed_power_date and changed_power_date != self.power_date:
                cached_property["d_order_line"].append(distribution_id.id)

        ids = self.env["distribution.order"].browse(distribution_ids).mapped('distribution_line_ids').ids
        self.distribution_line_ids = [(6, 0, ids)]

    def action_distribute(self):
        loadshape_details_ids = self.env['contract'].search([
            ("delivery_point_id", "=", self.env.context.get('default_delivery_point_id')),
            ("status", "=", "executing")
        ]).mapped('loadshape_details_ids').filtered(lambda l: l.powerdate == self.power_date)

        if not loadshape_details_ids:
            raise UserError(_('There is no loadshape items planned to use for distribution on chosen date.'))

        for line in self.distribution_line_ids:
            line.power_date = self.power_date

            if line.power and line.power_hour not in loadshape_details_ids.mapped("powerhour"):
                raise UserError(
                    _("There is no loadshape item planned to use for distribution on the chosen hour %s for this date.") % (
                        line.power_hour))
            available_power = sum(
                loadshape_details_ids.filtered(lambda l: l.powerhour == line.power_hour).mapped("power"))
            # get from line actual_power
            distributed_power = sum(self.distribution_line_ids.filtered(lambda l: l.power_hour == line.power_hour).mapped('power'))
            if distributed_power > available_power:
                raise UserError(
                    _("Distributed Power %s overpasses the available power %s for hour %s.") % (
                        distributed_power, available_power, line.power_hour))

            # delete 0 power lines - TODO
            # self.distribution_line_ids.filtered(lambda l: not l.power).unlink()
        # delete cached properties
        # self.env['contract'].browse(cached_property["contract"]).unlink()
        # self.env['contract'].browse(cached_property["d_order"]).unlink()
        # self.env['contract'].browse(cached_property["d_order_line"]).unlink()
        return {'type': 'ir.actions.act_window_close'}

