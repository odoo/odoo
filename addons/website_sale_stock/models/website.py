# -*- coding: utf-8 -*-
from odoo import api, models

class Website(models.Model):
    _inherit = 'website'

    @api.multi
    def _prepare_sale_order_values(self, partner, pricelist):
        self.ensure_one()
        values = super(Website, self)._prepare_sale_order_values(partner, pricelist)
        if values['company_id']:
            warehouse_id = (
                self.env['ir.default'].get('sale.order', 'warehouse_id', company_id=values.get('company_id')) or
                self.env['ir.default'].get('sale.order', 'warehouse_id') or
                self.env['stock.warehouse'].sudo().search([('company_id', '=', values['company_id'])], limit=1).id
            )
            if warehouse_id:
                values['warehouse_id'] = warehouse_id
        return values
