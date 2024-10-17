from odoo import api, fields, models


class UomUom(models.Model):
    _name = 'uom.uom'
    _inherit = ['uom.uom', 'pos.load.mixin']

    is_pos_groupable = fields.Boolean(string='Group Products in POS', compute='_compute_is_pos_groupable', store=True,
        help="Check if you want to group products of this unit in point of sale orders")

    @api.depends('relative_uom_id')
    def _compute_is_pos_groupable(self):
        for uom in self:
            uom.is_pos_groupable = uom.relative_uom_id.is_pos_groupable if uom.relative_uom_id else False

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'factor', 'is_pos_groupable']

    def _load_pos_data(self, data):
        domain = self._load_pos_data_domain(data)
        fields = self._load_pos_data_fields(data['pos.config'][0]['id'])
        return self.with_context({**self.env.context}).search_read(domain, fields, load=False)


class ProductUom(models.Model):
    _inherit = ['product.uom', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'product_id', 'uom_id']

    def _load_pos_data(self, data):
        domain = self._load_pos_data_domain(data)
        fields = self._load_pos_data_fields(data['pos.config'][0]['id'])
        return self.with_context({**self.env.context}).search_read(domain, fields, load=False)
