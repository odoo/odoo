from odoo import models, api


class ResCurrency(models.Model):
    _name = 'res.currency'
    _inherit = ['res.currency', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        company_currency_id = self.env['res.company'].browse(data['pos.config']['data'][0]['company_id']).currency_id.id
        if company_currency_id != data['pos.config']['data'][0]['currency_id']:
            return [('id', 'in', [company_currency_id, data['pos.config']['data'][0]['currency_id']])]
        return [('id', '=', data['pos.config']['data'][0]['currency_id'])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'symbol', 'position', 'rounding', 'rate', 'decimal_places', 'iso_numeric']
