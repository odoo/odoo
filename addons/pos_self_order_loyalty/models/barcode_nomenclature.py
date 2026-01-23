from odoo import models, api


class BarcodeNomenclature(models.Model):
    _name = 'barcode.nomenclature'
    _inherit = ['barcode.nomenclature', 'pos.load.mixin']

    @api.model
    def _load_pos_self_data_fields(self, config):
        return ["name", "rule_ids", "upc_ean_conv"]

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        return [('id', '=', config.company_id.nomenclature_id.id)]
