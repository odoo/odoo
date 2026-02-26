from odoo import models, api


class ResCurrency(models.Model):
    _name = 'res.currency'
    _inherit = ['res.currency', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        company_currency_id = config.company_id.currency_id.id
        journals = config.payment_method_ids.journal_id
        currency_ids = journals.currency_id.ids
        currency_ids.append(company_currency_id)
        return [('id', 'in', currency_ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'symbol', 'position', 'rounding', 'rate', 'decimal_places', 'iso_numeric']
