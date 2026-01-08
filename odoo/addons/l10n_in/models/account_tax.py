from odoo import api, fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_in_reverse_charge = fields.Boolean("Reverse charge", help="Tick this if this tax is reverse charge. Only for Indian accounting")

    @api.model
    def _get_generation_dict_from_base_line(self, line_vals, tax_vals, force_caba_exigibility=False):
        # EXTENDS account
        # Group taxes also by product.
        res = super()._get_generation_dict_from_base_line(line_vals, tax_vals, force_caba_exigibility=force_caba_exigibility)
        record = line_vals['record']
        if isinstance(record, models.Model)\
                and record._name == 'account.move.line'\
                and record.company_id.account_fiscal_country_id.code == 'IN':
            res['product_id'] = record.product_id.id
            res['product_uom_id'] = record.product_uom_id.id
        return res

    @api.model
    def _get_generation_dict_from_tax_line(self, line_vals):
        # EXTENDS account
        # Group taxes also by product.
        res = super()._get_generation_dict_from_tax_line(line_vals)
        record = line_vals['record']
        if isinstance(record, models.Model)\
                and record._name == 'account.move.line'\
                and record.company_id.account_fiscal_country_id.code == 'IN':
            res['product_id'] = record.product_id.id
            res['product_uom_id'] = record.product_uom_id.id
        return res
