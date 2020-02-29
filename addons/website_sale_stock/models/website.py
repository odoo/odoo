# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Website(models.Model):
    _inherit = 'website'

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')

    def _prepare_sale_order_values(self, partner, pricelist):
        self.ensure_one()
        values = super(Website, self)._prepare_sale_order_values(partner, pricelist)
        if values['company_id']:
            warehouse_id = (
                self.warehouse_id and self.warehouse_id.id or
                self.env['ir.default'].get('sale.order', 'warehouse_id', company_id=values.get('company_id')) or
                self.env['ir.default'].get('sale.order', 'warehouse_id') or
                self.env['stock.warehouse'].sudo().search([('company_id', '=', values['company_id'])], limit=1).id
            )
            if warehouse_id:
                values['warehouse_id'] = warehouse_id
        return values
