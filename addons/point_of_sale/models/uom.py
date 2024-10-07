from odoo import api, fields, models


class UomCategory(models.Model):
    _inherit = ['uom.category', 'pos.load.mixin']

    is_pos_groupable = fields.Boolean(string='Group Products in POS',
        help="Check if you want to group products of this category in point of sale orders")

    @api.model
    def _load_pos_data_domain(self, data):
        return [('uom_ids', 'in', [uom['category_id'] for uom in data['uom.uom']['data']])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'uom_ids']


class UomUom(models.Model):
    _inherit = ['uom.uom', 'pos.load.mixin']

    is_pos_groupable = fields.Boolean(related='category_id.is_pos_groupable', readonly=False)

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'category_id', 'factor_inv', 'factor', 'is_pos_groupable', 'uom_type', 'rounding']

    def _load_pos_data(self, data):
        domain = self._load_pos_data_domain(data)
        fields = self._load_pos_data_fields(data['pos.config']['data'][0]['id'])
        return {
            'data': self.with_context({**self.env.context}).search_read(domain, fields, load=False),
            'fields': fields,
        }
