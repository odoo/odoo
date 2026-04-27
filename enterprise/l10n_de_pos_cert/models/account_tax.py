# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import models
NON_TAXABLE_GRIDS = {'+21', '+45_BASE', '-21', '-45_BASE'}


class AccountTax(models.Model):
    _inherit = 'account.tax'

    def get_vat_definition_id(self):
        self.ensure_one()
        if not self.filtered(lambda t: t.company_id.is_country_germany and t.company_id.l10n_de_fiskaly_api_secret):
            return False  # or default value
        if not self.amount:
            all_tags = set((self.invoice_repartition_line_ids + self.refund_repartition_line_ids).tag_ids.mapped('name'))
            return 5 if all_tags.issubset(NON_TAXABLE_GRIDS) else 6
        # For other tax with amount, sort to prioritize standard VATs (lower IDs) over historical ones (higher IDs) when selecting the export ID
        if not self.company_id.get_vat_mapping_json():
            self.company_id.l10n_de_update_vat_export_data()
        sorted_vats = sorted(json.loads(self.company_id.get_vat_mapping_json()), key=lambda x: x['vat_definition_export_id'])
        vat_export_id = next((i['vat_definition_export_id'] for i in sorted_vats if i['percentage'] == self.amount), 0)
        if not vat_export_id:
            # For individual circumstances we have to create a new VAT definition with ID above 1000
            vat_definition_export_id = self.amount + 1000
            new_vat_response = self.company_id._l10n_de_fiskaly_dsfinvk_rpc('PUT', f'/vat_definitions/{vat_definition_export_id}', {'percentage': self.amount})
            if new_vat_response.status_code == 200:
                self.company_id.l10n_de_update_vat_export_data()
                sorted_vats = sorted(json.loads(self.company_id.get_vat_mapping_json()), key=lambda x: x['vat_definition_export_id'])
                return next(i['vat_definition_export_id'] for i in sorted_vats if i['percentage'] == self.amount)
        return vat_export_id
