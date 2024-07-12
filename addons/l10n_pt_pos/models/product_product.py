from odoo import api, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _load_pos_data_read(self, records, config):
        # EXTENDS point_of_sale
        # A till names its products as its own company does, whichever company is active.
        records = records.with_context(l10n_pt_frozen_product_name=config.company_id.account_fiscal_country_id.code == 'PT')
        return super()._load_pos_data_read(records, config)
