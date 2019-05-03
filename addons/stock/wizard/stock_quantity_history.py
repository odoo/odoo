# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class StockQuantityHistory(models.TransientModel):
    _name = 'stock.quantity.history'
    _description = 'Stock Quantity History'

    compute_at_date = fields.Selection([
        ('0', 'Current Inventory'),
        ('1', 'At a Specific Date')
    ], default='0', string="Compute", help="Choose to analyze the current inventory or from a specific date in the past.")
    date = fields.Datetime('Inventory at Date', help="Choose a date to get the inventory at that date", default=fields.Datetime.now)

    def open_table(self):
        self.ensure_one()

        if int(self.compute_at_date):
            tree_view_id = self.env.ref('stock.view_stock_product_tree').id
            form_view_id = self.env.ref('stock.product_form_view_procurement_button').id
            # We pass `to_date` in the context so that `qty_available` will be computed across
            # moves until date.
            action = {
                'type': 'ir.actions.act_window',
                'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
                'view_mode': 'tree,form',
                'name': _('Products'),
                'res_model': 'product.product',
                'domain': "[('type', '=', 'product')]",
                'context': dict(self.env.context, to_date=self.date),
            }
            return action
        else:
            self = self.with_context(search_default_internal_loc=1)
            if self.user_has_groups('stock.group_production_lot,stock.group_stock_multi_locations'):
                # fixme: erase the following condition when it'll be possible to create a new record
                # from a empty grouped editable list without go through the form view.
                if self.env['stock.quant'].search_count([
                    ('company_id', '=', self.env.user.company_id.id),
                    ('location_id.usage', 'in', ['internal', 'transit'])
                ]) > 0:
                    self = self.with_context(
                        search_default_productgroup=1,
                        search_default_locationgroup=1
                    )
            if not self.user_has_groups('stock.group_stock_multi_locations'):
                company_user = self.env.user.company_id
                warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
                if warehouse:
                    self = self.with_context(default_location_id=warehouse.lot_stock_id.id)

            # If user have rights to write on quant, we set quants in inventory mode.
            if self.user_has_groups('stock.group_stock_manager'):
                self = self.with_context(inventory_mode=True)
            return self.env['stock.quant']._get_quants_action(extend=True)
