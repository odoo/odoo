from odoo import models, api


class ResCurrency(models.Model):
    _name = 'res.currency'
    _inherit = ['res.currency', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        company_currency_id = config.company_id.currency_id.id
        config_currency_id = config.currency_id.id
        if company_currency_id != config_currency_id:
            return [('id', 'in', [company_currency_id, config_currency_id])]
        return [('id', '=', config_currency_id)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'symbol', 'position', 'rounding', 'rate', 'decimal_places', 'iso_numeric']
