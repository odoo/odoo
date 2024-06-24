from odoo import models, api, _


class Warehouse(models.Model):
    _inherit = "stock.warehouse"

    def _get_sequence_values(self, name=False, code=False):
        sequence_values = super()._get_sequence_values(name=name, code=code)
        if self.company_id.country_id.code != 'PT':
            return sequence_values
        sequence_values.get("out_type_id").update({
            'prefix': _("TMP/"),
            'suffix': _(" (temporary name)"),
        })
        return sequence_values

    @api.model
    def _l10n_pt_stock_update_picking_types(self):
        warehouses = self.env['stock.warehouse'].search([
            ("company_id.account_fiscal_country_id.code", "=", "PT"),
        ])
        for warehouse in warehouses:
            new_vals = warehouse._create_or_update_sequences_and_picking_types()
            warehouse.write(new_vals)
