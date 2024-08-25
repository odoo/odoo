from odoo import models


class ProductTemplateImportCSV(models.TransientModel):

    _inherit = 'base_import.import'

    def execute_import(self, fields, columns, options, dryrun=False):
        res = super().execute_import(fields, columns, options, dryrun=dryrun)
        if options.get('product_import'):
            location = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1).lot_stock_id.id
            templates = self.env['product.template'].browse(res.get('ids'))
            for template in templates:
                if template.product_variant_id.exists():
                    vals = {
                        'product_id': template.product_variant_id.id,
                        'location_id': location,
                        'inventory_quantity': template.create_onhand_qty_from_import,
                    }
                self.env['stock.quant'].with_context(inventory_mode=True).create(vals).action_apply_inventory()
        return res
