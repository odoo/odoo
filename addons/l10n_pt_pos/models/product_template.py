from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _load_pos_data_read(self, records, config):
        # EXTENDS point_of_sale
        # A till names its products as its own company does, whichever company is active: a Portuguese
        # till by their name on Portuguese documents, in its screens (`display_name`) and on its order
        # lines, which take their name from the template's `name`.
        records = records.with_context(l10n_pt_frozen_product_name=config.company_id.account_fiscal_country_id.code == 'PT')
        return super()._load_pos_data_read(records, config)
