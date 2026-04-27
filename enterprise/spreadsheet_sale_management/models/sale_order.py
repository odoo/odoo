# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    spreadsheet_template_id = fields.Many2one(
        'sale.order.spreadsheet',
        related='sale_order_template_id.spreadsheet_template_id',
    )
    spreadsheet_ids = fields.One2many(
        'sale.order.spreadsheet',
        'order_id',
        string="Spreadsheets",
        export_string_translation=False,
    )
    spreadsheet_id = fields.Many2one(
        'sale.order.spreadsheet',
        export_string_translation=False,
        compute='_compute_spreadsheet_id',
    )

    @api.onchange('spreadsheet_template_id')
    def _onchange_spreadsheet_template_id(self):
        self.spreadsheet_id = False

    @api.depends('spreadsheet_ids')
    def _compute_spreadsheet_id(self):
        for order in self:
            order.spreadsheet_id = order.spreadsheet_ids[:1]

    def action_open_sale_order_spreadsheet(self):
        self.ensure_one()
        if not self.spreadsheet_id:
            self.spreadsheet_template_id.copy({"order_id": self.id})
        return self.spreadsheet_id.action_open_spreadsheet()

    def copy(self, default=None):
        default = dict(default or {})
        sale_orders = super().copy(default=default)
        if 'spreadsheet_ids' not in default:
            for order, new_order in zip(self, sale_orders):
                # copy the spreadsheet, with all the revisions history
                new_order.spreadsheet_ids = order.spreadsheet_ids.copy({"order_id": new_order.id})
        return sale_orders

    def write(self, vals):
        if 'sale_order_template_id' in vals:
            for order in self:
                if vals['sale_order_template_id'] != order.sale_order_template_id.id and order.spreadsheet_id:
                    order.spreadsheet_ids.unlink()
        return super().write(vals)

    def unlink(self):
        for order in self:
            if order.spreadsheet_ids:
                order.spreadsheet_ids.unlink()
        return super().unlink()
