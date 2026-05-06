from odoo import api, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _load_pos_data_fields(self, config):
        fields = super()._load_pos_data_fields(config)
        fields += ['l10n_in_gst_tax_type']
        return fields

    def _prepare_base_line_grouping_key(self, base_line):
        # EXTENDS 'account'
        results = super()._prepare_base_line_grouping_key(base_line)
        results['l10n_in_hsn_code'] = base_line['l10n_in_hsn_code']
        results['product_uom_id'] = base_line['product_uom_id'].id if base_line['product_uom_id'] else False
        return results
