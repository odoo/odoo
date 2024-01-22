from odoo import models, fields


class ContractPrices(models.Model):
    _name = "contract_prices"
    _description = "Description of the Price Components model"

    value = fields.Float(string='Value')
    unit = fields.Selection([
        ('mwh', 'MWh'),
        ('kwh', 'kWh'),
        ('na', 'N/A')
    ], string='Unit')
    contract_id = fields.Many2one('contract', string='Contract')
    priceComponents_id = fields.Many2one('price_components', string='Price Components')

    def action_edit(self):
        pass

    def action_delete(self):
        pass
