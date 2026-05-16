from odoo import api, fields, models


class UomUom(models.Model):
    _name = 'uom.uom'
    _inherit = ['uom.uom', 'pos.load.mixin']

    is_pos_groupable = fields.Boolean(string='Group Products in POS', help="Check if you want to group products of this unit in point of sale orders")

    @api.model
    def _load_pos_data_fields(self, config):
        taxes = self.env['account.tax'].search(self.env['account.tax']._check_company_domain(config.company_id.id))
        product_uom_fields = taxes._eval_taxes_computation_prepare_product_uom_fields()
        return list(product_uom_fields.union({'id', 'name', 'factor', 'is_pos_groupable', 'parent_path', 'rounding'}))
