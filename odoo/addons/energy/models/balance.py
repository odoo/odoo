from odoo import api, fields, models
from datetime import datetime, timedelta

class EnergyBalance(models.Model):
    _name = "energy.balance"
    _description = "Energy Balance View"

    delivery_point_id = fields.Many2one('border', string='Delivery Point')
    date = fields.Date(string='Date')
    hour = fields.Selection([(str(i), f"{i:02d}:00 - {i+1:02d}:00") for i in range(24)], string='Hour')
    energy_balance = fields.Float(string='Energy Balance')

    @api.model
    def calculate_energy_balance(self):
        today = fields.Date.today()
        next_three_dates = [today + timedelta(days=i) for i in range(1, 4)]

        energy_balance_records = []
        for delivery_point in self.env['border'].search([]):
            for date in next_three_dates:

                records_to_delete = self.env['energy.balance'].search([
                    ('delivery_point_id', '=', self.delivery_point_id),
                    ('date', '=', date),
                ])
                records_to_delete.unlink()

                contracts_buy_listed = self.env['contract'].search([
                        ('delivery_point_id', '=', self.delivery_point_id),
                        ('start_date', '<=', date),
                        ('position', '=', 'buy'),
                        ('end_date', '>=', date)
                    ])
                contracts_sell_listed = self.env['contract'].search([
                        ('delivery_point_id', '=', self.delivery_point_id),
                        ('start_date', '<=', date),
                        ('position', '=', 'sell'),
                        ('end_date', '>=', date)
                    ])

                for hour in range(24):
                    buy_energy = sum(self.env['loadshape_details'].search([
                        ('contract_id', 'in', contracts_buy_listed),
                        ('powerhour', '=', str(hour))
                    ]).mapped('power'))

                    sell_energy = sum(self.env['contract'].search([
                        ('contract_id', 'in', contracts_sell_listed),
                        ('position', '=', 'sell'),
                        ('powerhour', '=', str(hour))
                    ]).mapped('power'))

                    energy_balance = buy_energy - sell_energy

                    energy_balance_records.append({
                        'delivery_point_id': self.delivery_point_id,
                        'date': date,
                        'hour': str(hour),
                        'energy_balance': energy_balance,
                    })
        self.env['energy.balance'].create(energy_balance_records)