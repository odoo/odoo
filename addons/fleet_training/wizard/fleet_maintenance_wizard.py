from odoo import fields, models


class FleetMaintenanceWizard(models.TransientModel):
    _name = 'fleet_training.maintenance.wizard'
    _description = 'Log Vehicle Maintenance'

    vehicle_id = fields.Many2one('fleet_training.vehicle', required=True)
    date = fields.Date(required=True, default=fields.Date.context_today)
    maintenance_type = fields.Selection(
        [
            ('service', 'Periodic Service'),
            ('repair', 'Repair'),
            ('tires', 'Tires'),
            ('other', 'Other'),
        ],
        default='service', required=True,
    )
    odometer = fields.Integer(string="Odometer (km)")
    cost = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    description = fields.Text()

    def action_confirm(self):
        self.ensure_one()
        self.env['fleet_training.maintenance'].create({
            'vehicle_id': self.vehicle_id.id,
            'date': self.date,
            'maintenance_type': self.maintenance_type,
            'odometer': self.odometer,
            'cost': self.cost,
            'description': self.description,
        })
        self.vehicle_id.action_set_maintenance()
        return {'type': 'ir.actions.act_window_close'}
