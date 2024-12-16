from odoo import api, models, _


class Warehouse(models.Model):
    _inherit = "stock.warehouse"

    def _get_sequence_values(self, name=False, code=False):
        sequence_values = super()._get_sequence_values(name=name, code=code)
        if self.company_id.country_id.code != 'PT':
            return sequence_values
        for sequence_type in ('out_type_id', 'int_type_id'):
            sequence_values.get(sequence_type).update({
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
