from odoo import api, fields, models


class PosDeliveryProvider(models.Model):
    _name = 'pos.delivery.provider'
    _description = 'Online Delivery Providers'

    name = fields.Char(string='Name', required=True, help='Name of the delivery provider i.e. Zomato, UberEats, etc.')
    technical_name = fields.Char(string='Provider Name', help='Technical name of the provider used by UrbanPiper')
    image_128 = fields.Image(string='Provider Image', max_width=128, max_height=128)
    journal_code = fields.Char(
        string='Journal Short Code',
        help='Short code of the journal to be used for journal creation'
    )
    available_country_ids = fields.Many2many(
        'res.country',
        string='Available Countries',
        help='Countries where this provider is available'
    )

    _sql_constraints = [('technical_name_uniq',
                         'unique(technical_name)',
                         'Provider Name must be unique.')]

    @api.model
    def _load_pos_data_domain(self, data):
        return []

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'technical_name']

    def _load_pos_data(self, data):
        domain = self._load_pos_data_domain(data)
        fields = self._load_pos_data_fields(data['pos.config']['data'][0]['id'])
        delivery_providers = self.search_read(domain, fields, load=False)
        return {
            'data': delivery_providers,
            'fields': fields,
        }
