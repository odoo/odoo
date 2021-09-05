# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError

class FleetConvertWizard(models.TransientModel):
    _name = 'hr.fleet.convert.wizard'
    _description = 'Convert external fleet to internal'

    @api.model
    def default_get(self, field_list=None):
        if self.env['fleet.category'].browse(self.env.context.get('active_id', None)).internal:
            raise UserError(_('This wizard can only be executed if the \'internal\' checkbox is unchecked.'))
        return super().default_get(field_list)

    def _default_line_ids(self):
        fleet_id = self.env['fleet.category'].browse(self.env.context.get('active_id', False))
        line_ids = []
        if fleet_id:
            lines = self.env['hr.fleet.convert.wizard.line']
            vehicles = fleet_id.vehicle_ids.filtered(lambda v: v.driver_id and not v.driver_employee_id)
            partners = vehicles.driver_id | vehicles.future_driver_id
            employees = self.env['hr.employee'].search([
                ('address_home_id', 'in', partners.ids)
            ])
            partner_employee_map = \
                {partner: employees.filtered(lambda e: e.address_home_id == partner) for partner in partners}
            for vehicle in vehicles:
                lines |= lines.new({
                    'vehicle_id': vehicle,
                    'employee_id': partner_employee_map[vehicle.driver_id][0] \
                        if vehicle.driver_id and partner_employee_map[vehicle.driver_id] else False,
                    'future_employee_id': partner_employee_map[vehicle.future_driver_id][0] \
                        if vehicle.future_driver_id and partner_employee_map[vehicle.future_driver_id] else False,
                })
            # Order invalids first, _order doesn't seem to affect the view
            line_ids = lines.sorted(key=lambda l: (
                    not l.invalid_driver, not l.invalid_future_driver, l.license_plate
                )
            )
        return line_ids

    fleet_id = fields.Many2one(
        'fleet.category',
        string='Fleet',
        default=lambda self: self.env.context.get('active_id', None),
        readonly=True,
    )
    line_ids = fields.One2many(
        'hr.fleet.convert.wizard.line',
        'convert_wizard_id',
        default=_default_line_ids,
    )

    def action_validate(self):
        for wizard in self:
            lines = wizard.line_ids
            wizard.fleet_id.write({'internal': True})
            lines.filtered(lambda l: l.invalid_driver).vehicle_id.write({'driver_id': False})
            lines.filtered(lambda l: l.invalid_future_driver).vehicle_id.write({'future_driver_id': False})
            for line in lines.filtered(lambda l: not l.invalid_driver):
                line.vehicle_id.write({
                    'driver_employee_id': line.employee_id.id,
                    'future_driver_employee_id': line.future_employee_id.id,
                })
        return True

class FleetConvertWizardLine(models.TransientModel):
    _name = 'hr.fleet.convert.wizard.line'
    _description = 'External fleet conversion data'
    _order = 'invalid_driver asc'

    convert_wizard_id = fields.Many2one('hr.fleet.convert.wizard', required=True, ondelete='cascade')
    vehicle_id = fields.Many2one('fleet.vehicle', required=False, ondelete='cascade')
    vehicle_name = fields.Char(related='vehicle_id.name', readonly=True)
    license_plate = fields.Char(related='vehicle_id.license_plate')
    driver_id = fields.Many2one(related='vehicle_id.driver_id')
    future_driver_id = fields.Many2one(related='vehicle_id.future_driver_id')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    future_employee_id = fields.Many2one('hr.employee', string='Future Employee')
    invalid_driver = fields.Boolean(compute='_compute_invalid')
    invalid_future_driver = fields.Boolean(compute='_compute_invalid')

    @api.depends('employee_id', 'future_employee_id')
    def _compute_invalid(self):
        invalids = self.filtered(lambda r: not r.employee_id or (r.employee_id and not r.employee_id.address_home_id))
        valids = (self - invalids)
        invalids.write({'invalid_driver': True})
        valids.write({'invalid_driver': False})
        invalids = self.filtered(lambda r: (r.future_driver_id and not r.future_employee_id) or \
            (r.future_employee_id and not r.future_employee_id.address_home_id))
        valids = (self - invalids)
        invalids.write({'invalid_future_driver': True})
        valids.write({'invalid_future_driver': False})
