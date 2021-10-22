# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Website(models.Model):
    _inherit = 'website'

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')

    def _prepare_sale_order_values(self, partner, pricelist):
        self.ensure_one()
        values = super(Website, self)._prepare_sale_order_values(partner, pricelist)
        if values['company_id']:
            warehouse_id = self._get_warehouse_available()
            if warehouse_id:
                values['warehouse_id'] = warehouse_id
        return values

    def _get_warehouse_available(self):
        return (
            self.warehouse_id and self.warehouse_id.id or
            self.env['ir.default'].get('sale.order', 'warehouse_id', company_id=self.company_id.id) or
            self.env['ir.default'].get('sale.order', 'warehouse_id') or
            self.env['stock.warehouse'].sudo().search([('company_id', '=', self.company_id.id)], limit=1).id
        )

    def sale_get_order(self, force_create=False, code=None, update_pricelist=False, force_pricelist=False):
        so = super().sale_get_order(force_create=force_create, code=code, update_pricelist=update_pricelist, force_pricelist=force_pricelist)
        return so.with_context(warehouse=so.warehouse_id.id) if so else so
