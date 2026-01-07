from odoo import models, api


class BarcodeRule(models.Model):
    _name = 'barcode.rule'
    _inherit = ['barcode.rule', 'pos.load.mixin']

    @api.model
    def _load_pos_self_data_fields(self, config):
        return ["name", "sequence", "type", "encoding", "pattern", "alias"]

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        return [('id', 'in', config.company_id.nomenclature_id.rule_ids.ids)]
