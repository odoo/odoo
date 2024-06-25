from odoo import models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    def _load_pos_self_data(self, data):
        domain = self._load_pos_self_data_domain(data)
        tax_ids = self.search(domain)
        taxes_list = []

        for tax in tax_ids:
            # Sudo because self_order user does not have access to _prepare_dict_for_taxes_computation
            taxes_list.append(tax.sudo()._prepare_dict_for_taxes_computation())

        if data.get('pos.config') and len(data['pos.config']['data']) > 0:
            product_fields = self.env['account.tax']._eval_taxes_computation_prepare_product_fields(taxes_list)
            data['pos.config']['data'][0]['_product_default_values'] = self.env['account.tax']._eval_taxes_computation_prepare_product_default_values(
                product_fields,
            )

        return {
            'data': taxes_list,
            'fields': self._load_pos_self_data_fields(data['pos.config']['data'][0]['id']),
        }
