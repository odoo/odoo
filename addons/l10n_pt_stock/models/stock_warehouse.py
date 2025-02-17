from odoo import api, models, _


class Warehouse(models.Model):
    _inherit = "stock.warehouse"

    @api.model
    def _l10n_pt_stock_update_picking_types(self):
        warehouses = self.env['stock.warehouse'].search([
            ("company_id.account_fiscal_country_id.code", "=", "PT"),
        ])
        for warehouse in warehouses:
            new_vals = warehouse._create_or_update_sequences_and_picking_types()
            warehouse.write(new_vals)
