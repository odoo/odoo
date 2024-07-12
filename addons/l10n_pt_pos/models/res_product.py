from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _load_pos_data_read(self, records, config):
        # EXTENDS point_of_sale
        # A Portuguese till names its products by their name on Portuguese documents: its order lines take
        # their name from the template's `name`, its screens from `display_name`.
        if config.company_id.account_fiscal_country_id.code != 'PT':
            return super()._load_pos_data_read(records, config)
        records = records.with_context(l10n_pt_frozen_product_name=True)
        read_records = super()._load_pos_data_read(records, config)
        pt_names = {template.id: template.l10n_pt_product_name for template in records.filtered('l10n_pt_product_name')}
        for values in read_records:
            if values['id'] in pt_names and 'name' in values:
                values['name'] = pt_names[values['id']]
        return read_records


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _load_pos_data_read(self, records, config):
        # EXTENDS point_of_sale
        if config.company_id.account_fiscal_country_id.code == 'PT':
            records = records.with_context(l10n_pt_frozen_product_name=True)
        return super()._load_pos_data_read(records, config)
