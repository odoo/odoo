from odoo import models, api


class AccountFiscalPosition(models.Model):
    _name = 'account.fiscal.position'
    _inherit = ['account.fiscal.position', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', 'in', data['pos.config']['data'][0]['fiscal_position_ids'])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'display_name']

    def _load_pos_data(self, data):
        domain = self._load_pos_data_domain(data)
        fields = self._load_pos_data_fields(data['pos.config']['data'][0]['id'])
        fiscal_position_ids = self.search(domain)
        fp_list = []

        for fiscal_position in fiscal_position_ids:
            fp_dict = fiscal_position.read(fields)[0]
            fp_dict['_tax_mapping_by_ids'] = {}

            for fiscal_position_tax in fiscal_position.tax_ids:
                if not fp_dict['_tax_mapping_by_ids'].get(fiscal_position_tax.tax_src_id.id):
                    fp_dict['_tax_mapping_by_ids'][fiscal_position_tax.tax_src_id.id] = []
                fp_dict['_tax_mapping_by_ids'][fiscal_position_tax.tax_src_id.id].append(fiscal_position_tax.tax_dest_id.id)

            fp_list.append(fp_dict)

        return {
            'data': fp_list,
            'fields': fields
        }
