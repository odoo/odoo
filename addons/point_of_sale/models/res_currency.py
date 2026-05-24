from odoo import models, api


class ResCurrency(models.Model):
    _name = 'res.currency'
    _inherit = ['res.currency', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        currency_ids = {config.company_id.currency_id.id, config.currency_id.id}
        currency_ids.update(pricelist['currency_id'] for pricelist in data['product.pricelist'])
        return [('id', 'in', list(currency_ids))]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'symbol', 'position', 'rounding', 'rate', 'decimal_places', 'iso_numeric']
